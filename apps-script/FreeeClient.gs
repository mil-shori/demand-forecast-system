/**
 * freee会計API クライアント（UrlFetchApp）
 *
 * - トークンの付与・自動リフレッシュは OAuth2 サービス（getFreeeService）に委譲
 * - 429（レート制限）時は Retry-After 秒（上限60秒）待って1回だけ再試行
 * - company_id は選択中の事業所を自動付与
 */

var FREEE_API_BASE = 'https://api.freee.co.jp';
var FREEE_API_VERSION = '2020-06-15';

/** GET リクエスト */
function freeeApiGet(path, params) {
  return freeeApiRequest('get', path, params, null);
}

/** POST リクエスト（JSONボディ） */
function freeeApiPost(path, body) {
  return freeeApiRequest('post', path, null, body);
}

function freeeApiRequest(method, path, params, body) {
  var service = getFreeeService();
  if (!service.hasAccess()) {
    throw new Error('freeeに接続されていません。サイドバーの「接続」タブから連携してください。');
  }

  var url = FREEE_API_BASE + path;
  if (params) {
    var q = Object.keys(params)
      .filter(function (k) { return params[k] !== null && params[k] !== undefined; })
      .map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]); })
      .join('&');
    if (q) url += '?' + q;
  }

  var options = {
    method: method,
    headers: {
      Authorization: 'Bearer ' + service.getAccessToken(),
      'X-Api-Version': FREEE_API_VERSION,
    },
    muteHttpExceptions: true,
  };
  if (body) {
    options.contentType = 'application/json';
    options.payload = JSON.stringify(body);
  }

  var resp = UrlFetchApp.fetch(url, options);

  // 429: レート制限 → Retry-After 待って1回だけ再試行
  if (resp.getResponseCode() === 429) {
    var retryAfter = Math.min(Number(resp.getHeaders()['Retry-After'] || 5), 60);
    Utilities.sleep(retryAfter * 1000);
    resp = UrlFetchApp.fetch(url, options);
  }

  var code = resp.getResponseCode();
  var text = resp.getContentText();
  if (code >= 400) {
    throw new Error('freee API エラー (' + code + '): ' + text);
  }
  return text ? JSON.parse(text) : {};
}

// --- 主要エンドポイント ---

function freeeGetAccountItems() {
  var data = freeeApiGet('/api/1/account_items', { company_id: getCompanyId() });
  return data.account_items || [];
}

function freeeGetPartners(keyword) {
  var params = { company_id: getCompanyId(), limit: 100 };
  if (keyword) params.keyword = keyword;
  var data = freeeApiGet('/api/1/partners', params);
  return data.partners || [];
}

/** 取引(deal)を作成。payload には company_id を自動付与 */
function freeeCreateDeal(payload) {
  payload.company_id = getCompanyId();
  var data = freeeApiPost('/api/1/deals', payload);
  return data.deal || {};
}

/** 損益計算書（試算表） */
function freeeGetTrialPl(fiscalYear, startMonth, endMonth) {
  var data = freeeApiGet('/api/1/reports/trial_pl', {
    company_id: getCompanyId(),
    fiscal_year: fiscalYear,
    start_month: startMonth,
    end_month: endMonth,
  });
  return data.trial_pl || {};
}

/** 勘定科目名 → ID を解決 */
function findAccountItemIdByName(accountItems, name) {
  for (var i = 0; i < accountItems.length; i++) {
    if (accountItems[i].name === name) return accountItems[i].id;
  }
  return null;
}
