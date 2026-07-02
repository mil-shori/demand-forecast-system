/**
 * 経理ロジック（既存 accounting_service.py の Apps Script 移植）
 *
 * - 売上集計（売上データシート → 期間×注文タイプ）
 * - 勘定科目の推定（マッピングシート → AI → デフォルト）
 * - freee への取引(deal)登録（仕訳ログシートで冪等性を担保）
 * - 経費の freee 同期
 */

var DEFAULT_SALES_ACCOUNT_NAME = '売上高';
var DEFAULT_EXPENSE_ACCOUNT_NAME = '雑費';

var ORDER_TYPE_LABELS = {
  subscription: '定期便売上',
  oneoff: '単発売上',
};

/**
 * 売上データを期間×注文タイプで集計する。
 * @param {string} startDate YYYY-MM-DD
 * @param {string} endDate   YYYY-MM-DD
 * @param {string} granularity 'daily' | 'monthly'
 */
function aggregateSales(startDate, endDate, granularity) {
  var data = readSheetObjects(SHEETS.SALES);
  var buckets = {}; // key: "period\torder_type"

  data.rows.forEach(function (row) {
    var iso = toIsoDate(row.order_date);
    if (!iso || iso < startDate || iso > endDate) return;
    var period = granularity === 'monthly' ? iso.slice(0, 7) : iso;
    var orderType = String(row.order_type || '').trim() || 'oneoff';
    var amount = Number(row.total_amount) || 0;
    if (amount <= 0) return;
    var key = period + '\t' + orderType;
    if (!buckets[key]) buckets[key] = { period: period, order_type: orderType, amount: 0, order_count: 0 };
    buckets[key].amount += amount;
    buckets[key].order_count += 1;
  });

  return Object.keys(buckets)
    .map(function (k) { return buckets[k]; })
    .sort(function (a, b) {
      return a.period < b.period ? -1 : a.period > b.period ? 1 :
        (a.order_type < b.order_type ? -1 : 1);
    });
}

/** マッピングシートから勘定科目を推定するリゾルバを構築 */
function buildResolver(mappingType) {
  var rows = readSheetObjects(SHEETS.MAPPINGS).rows
    .filter(function (m) {
      return String(m.mapping_type) === mappingType && (m.active === true || String(m.active).toLowerCase() === 'true');
    })
    .sort(function (a, b) { return (Number(b.priority) || 0) - (Number(a.priority) || 0); });

  return {
    resolve: function (sourceKey, description) {
      // 1. source_key 完全一致
      for (var i = 0; i < rows.length; i++) {
        if (String(rows[i].source_key) === String(sourceKey)) return rows[i];
      }
      // 2. keywords 部分一致
      var text = (sourceKey || '') + ' ' + (description || '');
      for (var j = 0; j < rows.length; j++) {
        var kw = String(rows[j].keywords || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
        for (var x = 0; x < kw.length; x++) {
          if (text.indexOf(kw[x]) >= 0) return rows[j];
        }
      }
      return null;
    },
  };
}

/** 売上集計から仕訳候補（プレビュー）を生成 */
function buildSalesEntries(startDate, endDate, granularity) {
  var resolver = buildResolver('SALES_CATEGORY');
  var sourceType = 'sales_' + granularity;
  var aggregates = aggregateSales(startDate, endDate, granularity);
  var journal = indexJournal();

  return aggregates.map(function (agg) {
    var sourceKey = agg.period + ':' + agg.order_type;
    var label = ORDER_TYPE_LABELS[agg.order_type] || '売上';
    var description = agg.period + ' ' + label + '（スプレッドシート自動連携 / ' + agg.order_count + '件）';
    var mapping = resolver.resolve(agg.order_type, description);
    var existing = journal[sourceType + '\t' + sourceKey];

    return {
      source_type: sourceType,
      source_key: sourceKey,
      category: agg.order_type,
      entry_date: granularity === 'daily' ? agg.period : agg.period + '-01',
      description: description,
      amount: agg.amount,
      order_count: agg.order_count,
      account_item_id: mapping && mapping.account_item_id ? Number(mapping.account_item_id) : null,
      account_item_name: mapping && mapping.account_item_name ? mapping.account_item_name : DEFAULT_SALES_ACCOUNT_NAME,
      tax_code: mapping && mapping.tax_code !== '' && mapping.tax_code != null ? Number(mapping.tax_code) : null,
      partner_id: mapping && mapping.partner_id !== '' && mapping.partner_id != null ? Number(mapping.partner_id) : null,
      already_synced: !!existing && existing.status === 'synced',
      existing_status: existing ? existing.status : null,
    };
  });
}

/** 仕訳ログを {source_type\tsource_key: row} で索引化 */
function indexJournal() {
  var idx = {};
  readSheetObjects(SHEETS.JOURNAL).rows.forEach(function (row) {
    idx[row.source_type + '\t' + row.source_key] = row;
  });
  return idx;
}

/** freee取引(deal)ペイロードを組み立てる */
function buildDealPayload(issueDate, dealType, amount, accountItemId, description, taxCode, partnerId) {
  var detail = {
    account_item_id: accountItemId,
    amount: Math.round(Number(amount)),
    description: String(description).slice(0, 255),
  };
  if (taxCode !== null && taxCode !== undefined) detail.tax_code = taxCode;
  var payload = { issue_date: issueDate, type: dealType, details: [detail] };
  if (partnerId !== null && partnerId !== undefined) payload.partner_id = partnerId;
  return payload;
}

/**
 * 売上集計をfreeeに収入取引として登録する。
 * 仕訳ログシートの (source_type, source_key) で冪等性を担保。
 * @param {boolean} dryRun true ならプレビューのみ返す
 */
function syncSalesToFreee(startDate, endDate, granularity, dryRun) {
  granularity = granularity || 'daily';
  var candidates = buildSalesEntries(startDate, endDate, granularity);

  if (dryRun) {
    return {
      dry_run: true,
      total: candidates.length,
      results: candidates.map(function (c) {
        return {
          source_key: c.source_key,
          entry_date: c.entry_date,
          description: c.description,
          amount: c.amount,
          account_item_name: c.account_item_name,
          status: c.already_synced ? 'skipped' : 'pending',
        };
      }),
    };
  }

  var accountItems = null; // 遅延ロード（マッピング未定義時のみ取得）
  var defaultId = null;
  var synced = 0, skipped = 0, failed = 0;
  var results = [];

  candidates.forEach(function (c) {
    if (c.already_synced) {
      skipped++;
      results.push({ source_key: c.source_key, amount: c.amount, account_item_name: c.account_item_name, status: 'skipped' });
      return;
    }
    try {
      var accountItemId = c.account_item_id;
      if (!accountItemId) {
        if (accountItems === null) accountItems = freeeGetAccountItems();
        var suggestion = aiSuggestAccountItemSafe(accountItems, c.description, c.category, 'income');
        if (suggestion) {
          accountItemId = suggestion.account_item_id;
          c.account_item_name = suggestion.account_item_name;
        } else {
          if (defaultId === null) defaultId = findAccountItemIdByName(accountItems, DEFAULT_SALES_ACCOUNT_NAME);
          if (!defaultId) throw new Error('勘定科目マッピングが未定義で、freee側に「' + DEFAULT_SALES_ACCOUNT_NAME + '」も見つかりません。');
          accountItemId = defaultId;
        }
      }
      var payload = buildDealPayload(c.entry_date, 'income', c.amount, accountItemId, c.description, c.tax_code, c.partner_id);
      var deal = freeeCreateDeal(payload);
      writeJournal(c.source_type, c.source_key, c.entry_date, 'SALES', c.description, c.amount, c.account_item_name, 'synced', deal.id, '');
      synced++;
      results.push({ source_key: c.source_key, amount: c.amount, account_item_name: c.account_item_name, status: 'synced', freee_deal_id: deal.id });
    } catch (e) {
      writeJournal(c.source_type, c.source_key, c.entry_date, 'SALES', c.description, c.amount, c.account_item_name, 'failed', '', String(e));
      failed++;
      results.push({ source_key: c.source_key, amount: c.amount, account_item_name: c.account_item_name, status: 'failed', error: String(e) });
    }
  });

  return { dry_run: false, total: candidates.length, synced: synced, skipped: skipped, failed: failed, results: results };
}

/** 仕訳ログシートへ upsert（source_type+source_key で一意） */
function writeJournal(sourceType, sourceKey, entryDate, entryType, description, amount, accountItemName, status, dealId, error) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEETS.JOURNAL);
  var existing = readSheetObjects(SHEETS.JOURNAL).rows.filter(function (r) {
    return r.source_type === sourceType && r.source_key === sourceKey;
  })[0];
  var syncedAt = status === 'synced' ? new Date().toISOString() : '';
  var rowValues = [sourceType, sourceKey, entryDate, entryType, description, amount, accountItemName, status, dealId || '', syncedAt, error || ''];
  if (existing) {
    sheet.getRange(existing._rowIndex, 1, 1, rowValues.length).setValues([rowValues]);
  } else {
    sheet.appendRow(rowValues);
  }
}

/**
 * 経費シートの未同期行をfreeeに支出取引として登録する。
 * @param {number} expenseId 経費のid。省略時は status!=synced の全行
 */
function syncExpensesToFreee(expenseId) {
  var resolver = buildResolver('EXPENSE_CATEGORY');
  var rows = readSheetObjects(SHEETS.EXPENSES).rows.filter(function (r) {
    if (expenseId != null) return String(r.id) === String(expenseId);
    return String(r.status || '').toLowerCase() !== 'synced';
  });
  if (rows.length === 0) return { total: 0, synced: 0, failed: 0, results: [] };

  var accountItems = null;
  var synced = 0, failed = 0;
  var results = [];

  rows.forEach(function (row) {
    try {
      var mapping = resolver.resolve(row.category, row.description || '');
      var accountItemId, taxCode = null, partnerId = null;
      if (mapping) {
        accountItemId = Number(mapping.account_item_id);
        taxCode = mapping.tax_code !== '' && mapping.tax_code != null ? Number(mapping.tax_code) : null;
        partnerId = mapping.partner_id !== '' && mapping.partner_id != null ? Number(mapping.partner_id) : null;
      } else {
        if (accountItems === null) accountItems = freeeGetAccountItems();
        var suggestion = aiSuggestAccountItemSafe(accountItems, row.description || '', row.category, 'expense');
        if (suggestion) {
          accountItemId = suggestion.account_item_id;
        } else {
          accountItemId = findAccountItemIdByName(accountItems, DEFAULT_EXPENSE_ACCOUNT_NAME);
          if (!accountItemId) throw new Error('経費カテゴリ「' + row.category + '」のマッピングが未定義で、freee側に「' + DEFAULT_EXPENSE_ACCOUNT_NAME + '」も見つかりません。');
        }
      }
      var desc = (row.category + ' ' + (row.description || '')).trim();
      var issueDate = toIsoDate(row.expense_date);
      var payload = buildDealPayload(issueDate, 'expense', row.amount, accountItemId, desc, taxCode, partnerId);
      var deal = freeeCreateDeal(payload);

      updateSheetCell(SHEETS.EXPENSES, row._rowIndex, 'status', 'synced');
      updateSheetCell(SHEETS.EXPENSES, row._rowIndex, 'freee_deal_id', deal.id);
      writeJournal('expense', 'expense:' + row.id, issueDate, 'EXPENSE', desc, row.amount, mapping ? mapping.account_item_name : '', 'synced', deal.id, '');
      synced++;
      results.push({ id: row.id, status: 'synced', freee_deal_id: deal.id });
    } catch (e) {
      updateSheetCell(SHEETS.EXPENSES, row._rowIndex, 'status', 'failed');
      failed++;
      results.push({ id: row.id, status: 'failed', error: String(e) });
    }
  });

  return { total: rows.length, synced: synced, failed: failed, results: results };
}

/** サイドバーから1件の経費を追加 */
function addExpense(expense) {
  initializeSheets();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEETS.EXPENSES);
  var existing = readSheetObjects(SHEETS.EXPENSES).rows;
  var nextId = existing.reduce(function (m, r) { return Math.max(m, Number(r.id) || 0); }, 0) + 1;
  sheet.appendRow([
    nextId, expense.expense_date, Number(expense.amount), expense.category,
    expense.description || '', expense.payment_method || 'cash', expense.partner_name || '', 'draft', '',
  ]);
  return { id: nextId };
}
