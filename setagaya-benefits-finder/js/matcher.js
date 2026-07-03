/**
 * 制度の絞り込み・書類チェックリスト生成ロジック（純粋関数）
 * ブラウザと Node.js（テスト）の両方から利用できます。
 *
 * profile の形式:
 * {
 *   pregnant: boolean,            // 妊娠中かどうか
 *   ages: string[],               // 子どもの年齢層（'0-2' | '3-5' | 'elementary' | 'junior' | 'high'）
 *   singleParent: boolean,        // ひとり親世帯
 *   disability: boolean,          // 障害のある子どもがいる
 *   childcare: string[],          // 利用中・利用予定の保育等（'ninka' | 'ninkagai' | 'yochien'）
 *   includeIncomeLimited: boolean // 所得制限のある制度も表示するか
 * }
 */

/**
 * 対象者（audience）に合致するか。
 * pregnancy と ages は「いずれか」を満たせばよい。
 */
function matchesAudience(audience, profile) {
  if (audience.pregnancy && profile.pregnant) {
    return true;
  }
  if (Array.isArray(audience.ages) && audience.ages.some((a) => profile.ages.includes(a))) {
    return true;
  }
  return false;
}

/**
 * 追加要件（requires）をすべて満たすか。
 */
function matchesRequires(requires, profile) {
  if (requires.singleParent && !profile.singleParent) {
    return false;
  }
  if (requires.disability && !profile.disability) {
    return false;
  }
  if (Array.isArray(requires.childcare) && !requires.childcare.some((c) => profile.childcare.includes(c))) {
    return false;
  }
  return true;
}

/**
 * プロフィールに合致する制度の一覧を返す。
 */
function matchBenefits(profile, benefits) {
  return benefits.filter((b) => {
    if (b.incomeLimit && !profile.includeIncomeLimited) {
      return false;
    }
    return matchesAudience(b.audience, profile) && matchesRequires(b.requires, profile);
  });
}

/**
 * 選択された制度から書類チェックリストを組み立てる。
 * 2つ以上の制度で必要になる書類は common にまとめる。
 */
function buildChecklist(selectedBenefits) {
  const docCount = new Map();
  selectedBenefits.forEach((b) => {
    b.documents.forEach((doc) => {
      docCount.set(doc, (docCount.get(doc) || 0) + 1);
    });
  });

  const common = [...docCount.entries()]
    .filter(([, count]) => count >= 2)
    .map(([doc]) => doc);

  const perBenefit = selectedBenefits.map((b) => ({
    id: b.id,
    name: b.name,
    window: b.window,
    url: b.url,
    notes: b.notes,
    documents: b.documents,
  }));

  return { common, perBenefit };
}

/**
 * チェックリストをプレーンテキスト（コピー・ダウンロード用）に整形する。
 */
function checklistToText(checklist, generatedDate) {
  const lines = [];
  lines.push('世田谷区 子育て支援 申請書類チェックリスト');
  lines.push(`作成日: ${generatedDate}`);
  lines.push('');
  lines.push('※ このリストは参考情報です。必要書類は状況により異なるため、');
  lines.push('   申請前に必ず各制度の公式ページまたは窓口でご確認ください。');
  lines.push('');

  if (checklist.common.length > 0) {
    lines.push('■ 複数の申請で共通して必要になる書類');
    checklist.common.forEach((doc) => lines.push(`  □ ${doc}`));
    lines.push('');
  }

  checklist.perBenefit.forEach((b) => {
    lines.push(`■ ${b.name}`);
    lines.push(`  申請窓口: ${b.window}`);
    b.documents.forEach((doc) => lines.push(`  □ ${doc}`));
    if (b.notes) {
      lines.push(`  ※ ${b.notes}`);
    }
    lines.push(`  公式ページ: ${b.url}`);
    lines.push('');
  });

  return lines.join('\n');
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { matchBenefits, buildChecklist, checklistToText, matchesAudience, matchesRequires };
}
