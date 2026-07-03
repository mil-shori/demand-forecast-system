/**
 * 絞り込み・チェックリスト生成ロジックのテスト
 * 実行: node --test setagaya-benefits-finder/tests/
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { BENEFITS, ALL_AGES } = require('../js/data.js');
const { matchBenefits, buildChecklist, checklistToText } = require('../js/matcher.js');

function profile(overrides = {}) {
  return {
    pregnant: false,
    ages: [],
    singleParent: false,
    disability: false,
    childcare: [],
    includeIncomeLimited: true,
    ...overrides,
  };
}

const idsOf = (benefits) => benefits.map((b) => b.id);

test('データの整合性: 必須フィールドがすべて揃っている', () => {
  const seen = new Set();
  for (const b of BENEFITS) {
    assert.ok(b.id && !seen.has(b.id), `id が重複または未設定: ${b.id}`);
    seen.add(b.id);
    assert.ok(b.name, `${b.id}: name がない`);
    assert.ok(b.category, `${b.id}: category がない`);
    assert.ok(b.url.startsWith('https://'), `${b.id}: url が https でない`);
    assert.ok(Array.isArray(b.documents) && b.documents.length > 0, `${b.id}: documents が空`);
    assert.ok(b.audience.pregnancy || (b.audience.ages && b.audience.ages.length > 0),
      `${b.id}: audience が空`);
    for (const age of b.audience.ages || []) {
      assert.ok(ALL_AGES.includes(age), `${b.id}: 不正な年齢キー ${age}`);
    }
  }
});

test('条件未入力の場合は何も表示しない', () => {
  assert.equal(matchBenefits(profile(), BENEFITS).length, 0);
});

test('妊娠中のみ: 妊娠・出産系の制度が表示され、子ども向け制度は表示されない', () => {
  const ids = idsOf(matchBenefits(profile({ pregnant: true }), BENEFITS));
  assert.ok(ids.includes('ninpu-kyufu'));
  assert.ok(ids.includes('kosodate-riyoken'));
  assert.ok(ids.includes('shussanhi-josei'));
  assert.ok(!ids.includes('jido-teate'), '子どもがいない場合は児童手当は表示しない');
  assert.ok(!ids.includes('shugaku-enjo'));
});

test('0〜2歳の子どもがいる場合: 基本の手当と0-2歳向け制度が表示される', () => {
  const ids = idsOf(matchBenefits(profile({ ages: ['0-2'] }), BENEFITS));
  assert.ok(ids.includes('jido-teate'));
  assert.ok(ids.includes('kodomo-iryohi'));
  assert.ok(ids.includes('018-support'));
  assert.ok(ids.includes('kosodate-riyoken'), '0-2歳は妊娠していなくても子育て利用券の対象');
  assert.ok(!ids.includes('ninpu-kyufu'), '妊娠していなければ妊婦給付は表示しない');
  assert.ok(!ids.includes('yochien-hojo'), '幼稚園を選んでいなければ幼稚園補助は表示しない');
});

test('ひとり親要件: フラグがない場合はひとり親向け制度を表示しない', () => {
  const base = idsOf(matchBenefits(profile({ ages: ['elementary'] }), BENEFITS));
  assert.ok(!base.includes('jido-fuyo-teate'));
  assert.ok(!base.includes('hitorioya-iryohi'));

  const single = idsOf(matchBenefits(profile({ ages: ['elementary'], singleParent: true }), BENEFITS));
  assert.ok(single.includes('jido-fuyo-teate'));
  assert.ok(single.includes('jido-ikusei-teate'));
  assert.ok(single.includes('hitorioya-iryohi'));
});

test('障害要件: フラグがある場合のみ障害児向け手当を表示する', () => {
  const base = idsOf(matchBenefits(profile({ ages: ['junior'] }), BENEFITS));
  assert.ok(!base.includes('tokubetsu-jido-fuyo'));

  const withDisability = idsOf(matchBenefits(profile({ ages: ['junior'], disability: true }), BENEFITS));
  assert.ok(withDisability.includes('tokubetsu-jido-fuyo'));
  assert.ok(withDisability.includes('shogaiji-fukushi-teate'));
  assert.ok(withDisability.includes('jido-ikusei-shogai'));
});

test('保育要件: 選択した施設種別に応じた補助のみ表示する', () => {
  const ninka = idsOf(matchBenefits(profile({ ages: ['0-2'], childcare: ['ninka'] }), BENEFITS));
  assert.ok(ninka.includes('hoikuryo-mushoka'));
  assert.ok(!ninka.includes('ninkagai-hojo'));

  const ninkagai = idsOf(matchBenefits(profile({ ages: ['0-2'], childcare: ['ninkagai'] }), BENEFITS));
  assert.ok(ninkagai.includes('ninkagai-hojo'));
  assert.ok(!ninkagai.includes('hoikuryo-mushoka'));

  const yochien = idsOf(matchBenefits(profile({ ages: ['3-5'], childcare: ['yochien'] }), BENEFITS));
  assert.ok(yochien.includes('yochien-hojo'));
});

test('所得制限フィルタ: オフにすると所得制限のある制度が除外される', () => {
  const all = matchBenefits(
    profile({ ages: ['elementary'], singleParent: true, includeIncomeLimited: true }), BENEFITS);
  const limited = matchBenefits(
    profile({ ages: ['elementary'], singleParent: true, includeIncomeLimited: false }), BENEFITS);

  assert.ok(all.some((b) => b.incomeLimit), '前提: 所得制限ありの制度が含まれる');
  assert.ok(limited.every((b) => !b.incomeLimit), '除外後は所得制限ありの制度が残らない');
  assert.ok(idsOf(limited).includes('jido-teate'), '所得制限のない児童手当は残る');
});

test('高校生年代のみ: 高校生を対象に含む制度だけが表示される', () => {
  const ids = idsOf(matchBenefits(profile({ ages: ['high'] }), BENEFITS));
  assert.ok(ids.includes('jido-teate'));
  assert.ok(ids.includes('kodomo-iryohi'));
  assert.ok(ids.includes('018-support'));
  assert.ok(!ids.includes('shugaku-enjo'), '就学援助は小中学生のみ');
  assert.ok(!ids.includes('byoji-hoiku'), '病児保育は小学生まで');
});

test('チェックリスト: 2制度以上で必要な書類が common にまとまる', () => {
  const selected = BENEFITS.filter((b) => ['jido-teate', 'shussanhi-josei'].includes(b.id));
  const checklist = buildChecklist(selected);

  assert.equal(checklist.perBenefit.length, 2);
  assert.ok(checklist.common.includes('振込先口座がわかるもの'),
    '両制度で必要な口座情報が共通書類に入る');
  assert.ok(!checklist.common.includes('出産費用の領収書・明細書'),
    '片方だけの書類は共通に入らない');
});

test('チェックリストのテキスト出力に制度名・書類・免責が含まれる', () => {
  const selected = BENEFITS.filter((b) => b.id === 'jido-teate');
  const text = checklistToText(buildChecklist(selected), '2026年7月3日');

  assert.match(text, /児童手当/);
  assert.match(text, /□ 児童手当 認定請求書/);
  assert.match(text, /作成日: 2026年7月3日/);
  assert.match(text, /公式ページ: https:\/\//);
  assert.match(text, /必ず各制度の公式ページまたは窓口でご確認ください/);
});
