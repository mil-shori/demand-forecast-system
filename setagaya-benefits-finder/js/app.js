/**
 * せたがや子育て支援ナビ 画面制御
 * データは js/data.js、絞り込みロジックは js/matcher.js を参照。
 */
(function () {
  'use strict';

  const form = document.getElementById('profile-form');
  const resultsSection = document.getElementById('results-section');
  const resultsSummary = document.getElementById('results-summary');
  const resultsList = document.getElementById('results-list');
  const checklistSection = document.getElementById('checklist-section');
  const checklistOutput = document.getElementById('checklist-output');
  const copyStatus = document.getElementById('copy-status');

  // チェックリストに追加された制度ID
  const selectedIds = new Set();
  let lastChecklistText = '';
  let lastChecklist = null;

  function readProfile() {
    return {
      pregnant: document.getElementById('pregnant').checked,
      ages: [...form.querySelectorAll('input[name="ages"]:checked')].map((el) => el.value),
      singleParent: document.getElementById('single-parent').checked,
      disability: document.getElementById('disability').checked,
      childcare: [...form.querySelectorAll('input[name="childcare"]:checked')].map((el) => el.value),
      includeIncomeLimited: document.getElementById('include-income-limited').checked,
    };
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function renderResults(matched) {
    resultsList.textContent = '';

    if (matched.length === 0) {
      resultsSummary.textContent = '条件に合致する制度が見つかりませんでした。';
      const empty = el('div', 'no-results',
        '条件を変えて再度お試しください。妊娠中・年齢のいずれかを選択すると基本の手当が表示されます。');
      resultsList.appendChild(empty);
      return;
    }

    resultsSummary.textContent = `${matched.length}件の制度があてはまる可能性があります。`;

    matched.forEach((b) => {
      const card = el('article', 'benefit-card');
      card.dataset.id = b.id;
      if (selectedIds.has(b.id)) card.classList.add('selected');

      const head = el('div', 'benefit-head');
      head.appendChild(el('h3', null, b.name));
      head.appendChild(el('span', 'tag tag-category', b.category));
      if (b.incomeLimit) head.appendChild(el('span', 'tag tag-income', '所得制限あり'));
      card.appendChild(head);

      card.appendChild(el('p', 'benefit-amount', b.amount));
      card.appendChild(el('p', 'benefit-summary', b.summary));
      card.appendChild(el('p', 'benefit-meta', `対象: ${b.target}`));
      card.appendChild(el('p', 'benefit-meta', `申請窓口: ${b.window}`));

      const foot = el('div', 'benefit-foot');

      const selectLabel = el('label', 'select-benefit');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = selectedIds.has(b.id);
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) {
          selectedIds.add(b.id);
        } else {
          selectedIds.delete(b.id);
        }
        card.classList.toggle('selected', checkbox.checked);
        renderChecklist();
      });
      selectLabel.appendChild(checkbox);
      selectLabel.appendChild(el('span', null, 'チェックリストに追加'));
      foot.appendChild(selectLabel);

      const link = el('a', null, '公式ページで確認する ↗');
      link.href = b.url;
      link.target = '_blank';
      link.rel = 'noopener';
      foot.appendChild(link);

      card.appendChild(foot);
      resultsList.appendChild(card);
    });
  }

  function todayLabel() {
    const d = new Date();
    return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
  }

  function renderChecklist() {
    const selected = BENEFITS.filter((b) => selectedIds.has(b.id));
    checklistOutput.textContent = '';
    copyStatus.textContent = '';

    if (selected.length === 0) {
      checklistSection.hidden = false;
      lastChecklistText = '';
      lastChecklist = null;
      checklistOutput.appendChild(el('p', 'checklist-empty',
        '上の一覧から制度を選ぶと、ここに提出書類のチェックリストが表示されます。'));
      return;
    }

    const checklist = buildChecklist(selected);
    const dateLabel = todayLabel();
    lastChecklistText = checklistToText(checklist, dateLabel);
    lastChecklist = checklist;

    checklistSection.hidden = false;
    checklistOutput.appendChild(el('p', 'checklist-date', `作成日: ${dateLabel}／選択した制度: ${selected.length}件`));

    if (checklist.common.length > 0) {
      const group = el('section', 'checklist-group common');
      group.appendChild(el('h3', null, '複数の申請で共通して必要になる書類'));
      group.appendChild(el('p', 'checklist-window', '先にそろえておくと申請がスムーズです。'));
      group.appendChild(buildItemList(checklist.common));
      checklistOutput.appendChild(group);
    }

    checklist.perBenefit.forEach((b) => {
      const group = el('section', 'checklist-group');
      group.appendChild(el('h3', null, b.name));
      group.appendChild(el('p', 'checklist-window', `申請窓口: ${b.window}`));
      group.appendChild(buildItemList(b.documents));
      if (b.notes) group.appendChild(el('p', 'checklist-note', `※ ${b.notes}`));
      const linkWrap = el('p', 'checklist-link');
      const link = el('a', null, '公式ページ・様式を確認する ↗');
      link.href = b.url;
      link.target = '_blank';
      link.rel = 'noopener';
      linkWrap.appendChild(link);
      group.appendChild(linkWrap);
      checklistOutput.appendChild(group);
    });

    checklistOutput.appendChild(el('p', 'checklist-note',
      '※ 必要書類は個別の状況により追加・省略される場合があります。申請前に必ず窓口または公式ページでご確認ください。'));
  }

  function buildItemList(docs) {
    const ul = el('ul', 'checklist-items');
    docs.forEach((doc) => {
      const li = document.createElement('li');
      const label = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      label.appendChild(cb);
      label.appendChild(el('span', null, doc));
      li.appendChild(label);
      ul.appendChild(li);
    });
    return ul;
  }

  function runSearch() {
    const profile = readProfile();
    const matched = matchBenefits(profile, BENEFITS);

    // 表示されなくなった制度は選択からも外す
    const matchedIds = new Set(matched.map((b) => b.id));
    [...selectedIds].forEach((id) => {
      if (!matchedIds.has(id)) selectedIds.delete(id);
    });

    renderResults(matched);
    resultsSection.hidden = false;
    renderChecklist();
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // サンドボックス環境（allow-formsなし）ではsubmitイベントが発火しないため
  // clickを主経路にし、submitはEnterキー操作向けの補助とする
  document.getElementById('search-btn').addEventListener('click', runSearch);
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    runSearch();
  });

  document.getElementById('reset-btn').addEventListener('click', () => {
    form.reset();
    selectedIds.clear();
    resultsSection.hidden = true;
    checklistSection.hidden = true;
    resultsList.textContent = '';
    checklistOutput.textContent = '';
  });

  document.getElementById('print-btn').addEventListener('click', () => {
    window.print();
  });

  /* ---- フォールバックモーダル ----
   * サンドボックス内表示などでダウンロード・クリップボードが
   * ブロックされる環境でも内容を取り出せるようにする。
   */
  const modal = document.getElementById('fallback-modal');
  const modalTitle = document.getElementById('modal-title');
  const modalHint = document.getElementById('modal-hint');
  const modalBody = document.getElementById('modal-body');

  function openModal(title, hint) {
    modalTitle.textContent = title;
    modalHint.textContent = hint;
    modalBody.textContent = '';
    modal.hidden = false;
  }

  function closeModal() {
    modal.hidden = true;
    modalBody.textContent = '';
  }

  document.getElementById('modal-close').addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.hidden) closeModal();
  });

  // ダウンロードを試みる（サンドボックスでブロックされても例外にはならない）
  function attemptDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }

  // クリップボードAPIが使えない環境向けの旧方式コピー
  function legacyCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.readOnly = true;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch (err) {
      ok = false;
    }
    ta.remove();
    return ok;
  }

  function showTextModal(text, hint) {
    openModal('チェックリスト（テキスト）', hint);
    const ta = document.createElement('textarea');
    ta.className = 'modal-textarea';
    ta.value = text;
    ta.readOnly = true;
    modalBody.appendChild(ta);
    ta.focus();
    ta.select();
  }

  document.getElementById('pdf-btn').addEventListener('click', () => {
    if (!lastChecklist) {
      copyStatus.textContent = '先に制度を選択してください。';
      return;
    }
    try {
      const { blob, pages } = createChecklistPdf(lastChecklist, todayLabel());
      attemptDownload(blob, '世田谷区子育て支援_提出書類チェックリスト.pdf');
      // ダウンロードがブロックされる環境向けに、常にプレビューも表示する
      openModal('PDFプレビュー',
        'ダウンロードが自動で始まらない場合は、下の画像を右クリック（スマートフォンは長押し）して「名前を付けて保存」してください。');
      pages.forEach((canvas, i) => {
        const img = document.createElement('img');
        img.src = canvas.toDataURL('image/jpeg', 0.85);
        img.alt = `チェックリスト ${i + 1}ページ目`;
        img.className = 'pdf-preview-page';
        modalBody.appendChild(img);
      });
      copyStatus.textContent = '';
    } catch (err) {
      copyStatus.textContent = 'PDFを作成できませんでした。テキストのコピーをご利用ください。';
    }
  });

  document.getElementById('copy-btn').addEventListener('click', async () => {
    if (!lastChecklistText) {
      copyStatus.textContent = '先に制度を選択してください。';
      return;
    }
    let ok = false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(lastChecklistText);
        ok = true;
      } catch (err) {
        ok = false;
      }
    }
    if (!ok) ok = legacyCopy(lastChecklistText);
    if (ok) {
      copyStatus.textContent = 'コピーしました！';
    } else {
      copyStatus.textContent = '';
      showTextModal(lastChecklistText,
        '自動コピーが使えない環境です。下の内容を全選択してコピーしてください。');
    }
  });

  document.getElementById('download-btn').addEventListener('click', () => {
    if (!lastChecklistText) {
      copyStatus.textContent = '先に制度を選択してください。';
      return;
    }
    const blob = new Blob([lastChecklistText], { type: 'text/plain;charset=utf-8' });
    attemptDownload(blob, '世田谷区子育て支援_提出書類チェックリスト.txt');
    copyStatus.textContent = 'ダウンロードが始まらない場合は「テキストをコピー」をご利用ください。';
  });
})();
