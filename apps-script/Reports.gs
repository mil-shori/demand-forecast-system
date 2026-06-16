/**
 * 月次レポート
 *
 * - collectMonthlyData: 当月の売上・経費・同期状況を集計（AIサマリーの入力にもなる）
 * - buildMonthlyReportSheet: 「月次レポート YYYY-MM」シートを生成
 */

/** 当月の売上・経費・仕訳同期状況を集計 */
function collectMonthlyData(year, month) {
  var mm = ('0' + month).slice(-2);
  var prefix = year + '-' + mm; // YYYY-MM
  var startDate = prefix + '-01';
  var endDate = prefix + '-31';

  var sales = aggregateSales(startDate, endDate, 'daily');
  var totalSales = sales.reduce(function (s, r) { return s + r.amount; }, 0);

  // 経費（当月分）をカテゴリ別に集計
  var expenseRows = readSheetObjects(SHEETS.EXPENSES).rows.filter(function (r) {
    return toIsoDate(r.expense_date).slice(0, 7) === prefix;
  });
  var byCat = {};
  expenseRows.forEach(function (r) {
    var cat = String(r.category || '未分類');
    if (!byCat[cat]) byCat[cat] = { category: cat, amount: 0, count: 0 };
    byCat[cat].amount += Number(r.amount) || 0;
    byCat[cat].count += 1;
  });
  var expenseByCategory = Object.keys(byCat).map(function (k) { return byCat[k]; });
  var totalExpenses = expenseByCategory.reduce(function (s, e) { return s + e.amount; }, 0);

  // 仕訳ログの当月同期状況
  var stats = { synced: 0, failed: 0, pending: 0 };
  readSheetObjects(SHEETS.JOURNAL).rows.forEach(function (r) {
    if (toIsoDate(r.entry_date).slice(0, 7) !== prefix) return;
    var st = String(r.status || '').toLowerCase();
    if (st === 'synced') stats.synced++;
    else if (st === 'failed') stats.failed++;
    else stats.pending++;
  });

  return {
    year: year, month: month,
    sales: sales, totalSales: totalSales,
    expenseByCategory: expenseByCategory, totalExpenses: totalExpenses,
    syncStats: stats,
  };
}

/** 「月次レポート YYYY-MM」シートを生成して内容を書き込む */
function buildMonthlyReportSheet(year, month) {
  var data = collectMonthlyData(year, month);
  var mm = ('0' + month).slice(-2);
  var sheetName = '月次レポート ' + year + '-' + mm;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (sheet) ss.deleteSheet(sheet);
  sheet = ss.insertSheet(sheetName, 0);

  var rows = [];
  rows.push([year + '年' + month + '月 月次レポート', '']);
  rows.push(['生成日時', Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm')]);
  rows.push(['', '']);
  rows.push(['■ サマリー', '']);
  rows.push(['売上合計', data.totalSales]);
  rows.push(['経費合計', data.totalExpenses]);
  rows.push(['営業利益（概算）', data.totalSales - data.totalExpenses]);
  rows.push(['', '']);
  rows.push(['■ 売上明細（日別 × 種別）', '']);
  rows.push(['日付/種別', '金額', '件数']);
  data.sales.forEach(function (s) {
    rows.push([s.period + ' / ' + (ORDER_TYPE_LABELS[s.order_type] || s.order_type), s.amount, s.order_count]);
  });
  rows.push(['', '']);
  rows.push(['■ 経費（カテゴリ別）', '']);
  rows.push(['カテゴリ', '金額', '件数']);
  data.expenseByCategory.forEach(function (e) {
    rows.push([e.category, e.amount, e.count]);
  });
  rows.push(['', '']);
  rows.push(['■ freee同期状況', '']);
  rows.push(['登録済み', data.syncStats.synced]);
  rows.push(['失敗', data.syncStats.failed]);
  rows.push(['未送信', data.syncStats.pending]);

  // 各行の最大列数に合わせて整形
  var maxCols = rows.reduce(function (m, r) { return Math.max(m, r.length); }, 0);
  rows = rows.map(function (r) { while (r.length < maxCols) r.push(''); return r; });
  sheet.getRange(1, 1, rows.length, maxCols).setValues(rows);
  sheet.getRange(1, 1, 1, maxCols).setFontSize(14).setFontWeight('bold');
  sheet.setColumnWidth(1, 280);
  sheet.autoResizeColumns(2, maxCols - 1);
  ss.setActiveSheet(sheet);

  return { sheetName: sheetName, totalSales: data.totalSales, totalExpenses: data.totalExpenses };
}
