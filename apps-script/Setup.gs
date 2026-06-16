/**
 * スプレッドシートのデータモデル定義とセットアップ
 *
 * PostgreSQL のテーブルに相当するものを、スプレッドシートの各シートで表現する:
 *  - 売上データ        ... 既存システムの orders 相当（同期の入力）
 *  - 経費             ... expenses 相当
 *  - 勘定科目マッピング  ... account_item_mappings 相当（カテゴリ→勘定科目）
 *  - 仕訳ログ          ... journal_entries 相当（freee登録の結果・冪等性キー）
 */

var SHEETS = {
  SALES: '売上データ',
  EXPENSES: '経費',
  MAPPINGS: '勘定科目マッピング',
  JOURNAL: '仕訳ログ',
};

var HEADERS = {
  SALES: ['order_id', 'user_id', 'order_date', 'order_type', 'total_amount'],
  EXPENSES: ['id', 'expense_date', 'amount', 'category', 'description',
             'payment_method', 'partner_name', 'status', 'freee_deal_id'],
  MAPPINGS: ['mapping_type', 'source_key', 'keywords', 'account_item_id',
             'account_item_name', 'tax_code', 'partner_id', 'priority', 'active'],
  JOURNAL: ['source_type', 'source_key', 'entry_date', 'entry_type', 'description',
            'amount', 'account_item_name', 'status', 'freee_deal_id', 'synced_at', 'error'],
};

/** 全シートが初期化済みか */
function areSheetsInitialized() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  return Object.keys(SHEETS).every(function (k) {
    return ss.getSheetByName(SHEETS[k]) !== null;
  });
}

/** テンプレートシートを作成（既存はヘッダーのみ整える） */
function initializeSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  Object.keys(SHEETS).forEach(function (k) {
    var name = SHEETS[k];
    var sheet = ss.getSheetByName(name) || ss.insertSheet(name);
    var headers = HEADERS[k];
    var range = sheet.getRange(1, 1, 1, headers.length);
    range.setValues([headers]).setFontWeight('bold').setBackground('#e8eaed');
    sheet.setFrozenRows(1);
  });
  SpreadsheetApp.getActiveSpreadsheet().toast('シートを初期化しました', '経理アシスタント', 5);
  return { ok: true };
}

/** デモ用サンプルデータを投入 */
function seedSampleData() {
  initializeSheets();
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // 売上データ（2026-05の定期便/単発）
  var sales = ss.getSheetByName(SHEETS.SALES);
  if (sales.getLastRow() <= 1) {
    sales.getRange(2, 1, 8, 5).setValues([
      ['O-1001', 'U-01', '2026-05-01', 'subscription', 5000],
      ['O-1002', 'U-02', '2026-05-01', 'subscription', 5000],
      ['O-1003', 'U-03', '2026-05-01', 'oneoff', 3200],
      ['O-1004', 'U-04', '2026-05-02', 'subscription', 5000],
      ['O-1005', 'U-05', '2026-05-02', 'oneoff', 4800],
      ['O-1006', 'U-06', '2026-05-03', 'subscription', 5000],
      ['O-1007', 'U-07', '2026-05-03', 'oneoff', 2600],
      ['O-1008', 'U-08', '2026-05-03', 'subscription', 5000],
    ]);
  }

  // 経費
  var expenses = ss.getSheetByName(SHEETS.EXPENSES);
  if (expenses.getLastRow() <= 1) {
    expenses.getRange(2, 1, 2, HEADERS.EXPENSES.length).setValues([
      [1, '2026-05-10', 1200, '交通費', '客先訪問のタクシー代', 'cash', '', 'draft', ''],
      [2, '2026-05-15', 8000, '会議費', 'チームランチ', 'credit_card', '', 'draft', ''],
    ]);
  }

  // 勘定科目マッピング（定期便売上を「売上高」に。account_item_id は接続後に実IDへ要更新）
  var mappings = ss.getSheetByName(SHEETS.MAPPINGS);
  if (mappings.getLastRow() <= 1) {
    mappings.getRange(2, 1, 1, HEADERS.MAPPINGS.length).setValues([
      ['SALES_CATEGORY', 'subscription', '定期,サブスク', '', '売上高', '', '', 10, true],
    ]);
  }

  SpreadsheetApp.getActiveSpreadsheet().toast('サンプルデータを投入しました', '経理アシスタント', 5);
  return { ok: true };
}

// --- シート読み書きヘルパー ---

/** シートを {headers, rows:[{col:value}], range} として読む */
function readSheetObjects(sheetName) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet || sheet.getLastRow() < 2) return { headers: [], rows: [] };
  var values = sheet.getDataRange().getValues();
  var headers = values[0];
  var rows = [];
  for (var r = 1; r < values.length; r++) {
    var obj = { _rowIndex: r + 1 }; // 1-based シート行番号
    for (var c = 0; c < headers.length; c++) {
      obj[headers[c]] = values[r][c];
    }
    rows.push(obj);
  }
  return { headers: headers, rows: rows };
}

/** 日付セル（Date or 文字列）を YYYY-MM-DD に正規化 */
function toIsoDate(value) {
  if (value instanceof Date) {
    return Utilities.formatDate(value, 'Asia/Tokyo', 'yyyy-MM-dd');
  }
  return String(value).trim().slice(0, 10);
}

/** 指定シートの特定行・特定列を更新（ヘッダー名で列を解決） */
function updateSheetCell(sheetName, rowIndex, headerName, value) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var col = headers.indexOf(headerName) + 1;
  if (col > 0) sheet.getRange(rowIndex, col).setValue(value);
}
