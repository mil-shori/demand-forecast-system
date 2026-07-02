/**
 * freee OAuth2 認可コードフロー（apps-script-oauth2 ライブラリ利用）
 *
 * - client_id / client_secret は Script Properties に保存
 * - アクセストークン / リフレッシュトークンは OAuth2 ライブラリが UserProperties に保存し、
 *   期限切れ時は getAccessToken() が自動でリフレッシュする（freeeのrefresh_tokenローテーションにも追随）
 * - 選択中の事業所(company_id)は UserProperties に保存
 *
 * freee開発者アプリ側の callback URL には、次を登録してください:
 *   https://script.google.com/macros/d/{SCRIPT_ID}/usercallback
 *   （SCRIPT_ID は「プロジェクトの設定」または getRedirectUri() で確認できます）
 */

var FREEE_AUTH_BASE = 'https://accounts.secure.freee.co.jp';
var PROP_COMPANY_ID = 'FREEE_COMPANY_ID';
var PROP_COMPANY_NAME = 'FREEE_COMPANY_NAME';

/** freee OAuth2 サービスを構築 */
function getFreeeService() {
  var props = PropertiesService.getScriptProperties();
  var clientId = props.getProperty('FREEE_CLIENT_ID');
  var clientSecret = props.getProperty('FREEE_CLIENT_SECRET');
  if (!clientId || !clientSecret) {
    throw new Error(
      'FREEE_CLIENT_ID / FREEE_CLIENT_SECRET が未設定です。' +
      'スクリプトのプロジェクト設定 → スクリプト プロパティに登録してください。'
    );
  }
  return OAuth2.createService('freee')
    .setAuthorizationBaseUrl(FREEE_AUTH_BASE + '/public_api/authorize')
    .setTokenUrl(FREEE_AUTH_BASE + '/public_api/token')
    .setClientId(clientId)
    .setClientSecret(clientSecret)
    .setCallbackFunction('authCallback')
    .setPropertyStore(PropertiesService.getUserProperties())
    .setCache(CacheService.getUserCache());
}

/** OAuth2 コールバック（freeeからのリダイレクトを受ける） */
function authCallback(request) {
  var service = getFreeeService();
  var authorized = service.handleCallback(request);
  if (authorized) {
    // 接続直後に事業所一覧を取得し、未選択なら先頭を既定にする
    try {
      ensureCompanySelected();
    } catch (err) {
      // 事業所取得失敗はここでは握りつぶし、サイドバー側で再取得させる
    }
    return HtmlService.createHtmlOutput(
      '<p style="font-family:sans-serif">freeeとの接続が完了しました。このタブを閉じて、スプレッドシートのサイドバーに戻ってください。</p>'
    );
  }
  return HtmlService.createHtmlOutput(
    '<p style="font-family:sans-serif">接続に失敗しました。もう一度お試しください。</p>'
  );
}

/** 認可URLとリダイレクトURIを返す（サイドバーが新規タブで開く用） */
function getAuthUrl() {
  var service = getFreeeService();
  return {
    authorizationUrl: service.getAuthorizationUrl(),
    redirectUri: getRedirectUri(),
  };
}

/** freee開発者アプリに登録すべきコールバックURL */
function getRedirectUri() {
  return 'https://script.google.com/macros/d/' + ScriptApp.getScriptId() + '/usercallback';
}

/** メニューからの「freeeに接続」: 認可URLをダイアログで案内 */
function showAuthPrompt() {
  var info = getAuthUrl();
  var html = HtmlService.createHtmlOutput(
    '<div style="font-family:sans-serif;padding:8px">' +
    '<p>下のボタンからfreeeにログインして連携を許可してください。</p>' +
    '<p><a href="' + info.authorizationUrl + '" target="_blank" rel="noopener">freeeに接続する</a></p>' +
    '<hr><p style="font-size:11px;color:#666">freee開発者アプリのコールバックURLにこのURLを登録してください:<br>' +
    '<code style="word-break:break-all">' + info.redirectUri + '</code></p></div>'
  ).setWidth(420).setHeight(220);
  SpreadsheetApp.getUi().showModalDialog(html, 'freee連携');
}

/** 接続状態・事業所情報を返す */
function getFreeeStatus() {
  var props = PropertiesService.getScriptProperties();
  var configured = !!(props.getProperty('FREEE_CLIENT_ID') && props.getProperty('FREEE_CLIENT_SECRET'));
  if (!configured) {
    return { configured: false, connected: false, message: 'FREEE_CLIENT_ID / FREEE_CLIENT_SECRET が未設定です。' };
  }
  var service = getFreeeService();
  var connected = service.hasAccess();
  var userProps = PropertiesService.getUserProperties();
  return {
    configured: true,
    connected: connected,
    companyId: userProps.getProperty(PROP_COMPANY_ID),
    companyName: userProps.getProperty(PROP_COMPANY_NAME),
    redirectUri: getRedirectUri(),
  };
}

/** freeeの事業所一覧を取得 */
function listCompanies() {
  var data = freeeApiGet('/api/1/companies', null);
  return (data.companies || []).map(function (c) {
    return { id: c.id, name: c.display_name || c.name };
  });
}

/** 使用する事業所を選択 */
function setCompany(companyId, companyName) {
  var userProps = PropertiesService.getUserProperties();
  userProps.setProperty(PROP_COMPANY_ID, String(companyId));
  if (companyName) userProps.setProperty(PROP_COMPANY_NAME, companyName);
  return getFreeeStatus();
}

/** 事業所が未選択なら先頭を既定に設定 */
function ensureCompanySelected() {
  var userProps = PropertiesService.getUserProperties();
  if (userProps.getProperty(PROP_COMPANY_ID)) return;
  var companies = listCompanies();
  if (companies.length > 0) {
    setCompany(companies[0].id, companies[0].name);
  }
}

/** 現在選択中の事業所ID（未選択ならエラー） */
function getCompanyId() {
  var id = PropertiesService.getUserProperties().getProperty(PROP_COMPANY_ID);
  if (!id) {
    throw new Error('事業所が選択されていません。サイドバーの「接続」タブで事業所を選んでください。');
  }
  return Number(id);
}

/** freee接続を解除 */
function disconnectFreee() {
  var service = getFreeeService();
  service.reset();
  var userProps = PropertiesService.getUserProperties();
  userProps.deleteProperty(PROP_COMPANY_ID);
  userProps.deleteProperty(PROP_COMPANY_NAME);
  return { connected: false };
}
