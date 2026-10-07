class PriceHistoryComponent extends HTMLElement {
    constructor() {
        super();
        this.rowIndex = 0;
    }

    connectedCallback() {
        this.mode = this.getAttribute('mode') || 'edit';
        this.showDiff = this.getAttribute('show-diff') === 'true';
        this.editable = this.getAttribute('editable') !== 'false';

        console.log('PriceHistoryComponent connected:', {
            mode: this.mode,
            showDiff: this.showDiff,
            editable: this.editable,
            historiesAttr: this.getAttribute('histories')
        });

        this.render();
        this.setupEventListeners();
    }

    render() {
        const isApprovalMode = this.mode === 'approval';
        this.innerHTML = `
            <div class="table-responsive">
                <table class="table table-sm" id="priceHistoryTable">
                    <thead>
                        <tr>
                            <th>年度</th>
                            <th>適用年月</th>
                            <th>仕切価格</th>
                            <th>県連価格</th>
                            <th>参考小売価格</th>
                            <th>送料</th>
                            <th class="text-nowrap">粗利率<button type="button" class="btn btn-sm btn-link p-0 text-primary ms-1" data-bs-toggle="modal" data-bs-target="#grossMarginModal" title="粗利率管理">⚙️</button></th>
                            ${!isApprovalMode ? '<th>改定額</th>' : ''}
                            <th>改定理由</th>
                            <th>メモ</th>
                            ${!isApprovalMode ? '<th>操作</th>' : ''}
                        </tr>
                    </thead>
                    <tbody>
                        ${this.renderExistingRows()}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderExistingRows() {
        const histories = JSON.parse(this.getAttribute('histories') || '[]');
        console.log('renderExistingRows histories:', histories);

        const isApprovalMode = this.mode === 'approval';

        return histories.map(history => {
            console.log('Processing history:', history.id, 'gross_margin_rate:', history.gross_margin_rate);

            const isDiffRow = this.showDiff && history.diff_flags;
            const isDeleteRequest = history.is_delete_request;

            let rowClass = '';
            let rowStyle = '';

            if (isDeleteRequest) {
                rowClass = 'text-danger fw-bold';
                rowStyle = 'text-decoration: line-through;';
            } else if (!isApprovalMode && !history.is_editable) {
                rowClass = 'table-secondary';
                rowStyle = 'color: #6c757d;';
            }

            const grossMarginDisplay = this.getGrossMarginDisplay(history);
            console.log('Final gross margin display for history', history.id, ':', grossMarginDisplay);

            return `
                <tr data-id="${history.id}" class="${rowClass}" style="${rowStyle}">
                    <td>${history.period_year}年度</td>
                    <td>${history.effective_year_month}</td>
                    <td class="${this.getCellClass(history, 'wholesale_price', isDiffRow)}" ${this.getCellAttributes(history, 'wholesale_price')}>${this.formatPrice(history.wholesale_price)}</td>
                    <td class="kenren-price-cell ${this.getCellClass(history, 'kenren_price', isDiffRow)}" ${this.getCellAttributes(history, 'kenren_price')} style="${this.getKenrenPriceStyle(history)}">${this.formatPrice(this.getKenrenPriceDisplay(history))}</td>
                    <td class="${this.getCellClass(history, 'retail_price', isDiffRow)}" ${this.getCellAttributes(history, 'retail_price')}>${this.formatPrice(history.retail_price)}</td>
                    <td class="${this.getCellClass(history, 'shipping_fee', isDiffRow)}" ${this.getCellAttributes(history, 'shipping_fee')}>${this.formatShippingFee(history.shipping_fee || (isDiffRow ? '' : '-'))}</td>
                    <td>${grossMarginDisplay}</td>
                    ${!isApprovalMode ? `<td>${history.revision_amount !== null && history.revision_amount !== undefined ? history.revision_amount : '自動算出'}</td>` : ''}
                    <td class="${this.getCellClass(history, 'revision_reason', isDiffRow)}" ${this.getCellAttributes(history, 'revision_reason')}>${history.revision_reason || (isDiffRow ? '' : '-')}</td>
                    <td class="${this.getCellClass(history, 'memo', isDiffRow)}" ${this.getCellAttributes(history, 'memo')}>${history.memo || (isDiffRow ? '' : '-')}</td>
                    ${!isApprovalMode ? `<td>${this.getActionCell(history)}</td>` : ''}
                </tr>
            `;
        }).join('');
    }

    setupEventListeners() {
        if (this.mode === 'approval') {
            // 承認モードでも送料クリックイベントは有効にする
            this.addEventListener('click', (e) => {
                if (e.target.classList.contains('shipping-fee-truncated')) {
                    const fullText = e.target.dataset.fullText;
                    if (fullText && window.showShippingFeeModal) {
                        window.showShippingFeeModal(fullText);
                    }
                }
            });
            return; // 承認モードでは他のイベントリスナーは設定しない
        }

        // 初期状態でボタン状態を更新
        this.updateAddButtonState();

        // 送料クリックイベント
        this.addEventListener('click', (e) => {
            if (e.target.classList.contains('shipping-fee-truncated')) {
                const fullText = e.target.dataset.fullText;
                if (fullText && window.showShippingFeeModal) {
                    window.showShippingFeeModal(fullText);
                }
            }
        });

        // イベント委譲でボタンクリックを処理
        this.addEventListener('click', (e) => {
            const action = e.target.dataset.action;

            switch (action) {
                case 'add-new-row':
                    this.addPriceRow();
                    break;
                case 'remove-new-row':
                    this.removeNewRow(e.target);
                    break;
                case 'mark-delete':
                    this.markForDeletion(e.target);
                    break;
            }
        });

        // 編集可能セルのクリックイベント
        this.addEventListener('click', (e) => {
            if (e.target.classList.contains('editable-cell')) {
                this.startInlineEdit(e.target);
            }
        });

        // 日付入力のイベント処理
        this.addEventListener('blur', (e) => {
            console.log('Blur event:', e.target.className, e.target.dataset.rowIndex);
            if (e.target.classList.contains('date-input')) {
                const rowIndex = e.target.dataset.rowIndex;
                console.log('Date input blur, rowIndex:', rowIndex);
                if (rowIndex) {
                    this.updatePeriodAndMargin(parseInt(rowIndex));
                }
            }
        }, true);

        this.addEventListener('change', (e) => {
            console.log('Change event:', e.target.className, e.target.dataset.rowIndex);
            if (e.target.classList.contains('date-input')) {
                const rowIndex = e.target.dataset.rowIndex;
                console.log('Date input change, rowIndex:', rowIndex);
                if (rowIndex) {
                    this.updatePeriodAndMargin(parseInt(rowIndex));
                }
            }
        });
    }

    // 新規行追加機能
    addPriceRow() {
        if (this.mode === 'approval') return; // 承認モードでは追加不可

        const tbody = this.querySelector('#priceHistoryTable tbody');

        // 既に新規行があるかチェック
        const existingNewRow = tbody.querySelector('tr[data-id="new"]');
        if (existingNewRow) {
            alert('新規行は1つまでしか追加できません。');
            const firstInput = existingNewRow.querySelector('input');
            if (firstInput) {
                firstInput.focus();
            }
            return;
        }

        // --- 2026/06/04【ここから追加】前行（既存の最新行）の送料を取得する処理 ---
        let beforeShippingFee = "";
        // 現在テーブル内にある最初の行（インライン編集用のセル、または通常セル）を探す
        const firstRow = tbody.querySelector('tr');
        if (firstRow) {
            // ケースA: インライン編集中の textarea や input があればその値を取得
            const editingTextarea = firstRow.querySelector('td[data-field="shipping_fee"] textarea, td[data-field="shipping_fee"] input');
            if (editingTextarea) {
                beforeShippingFee = editingTextarea.value;
            } else {
                // ケースB: 通常表示状態の場合、data-full-text 属性（ポップアップ用改行保持データ）か textContent から取得
                const truncatedSpan = firstRow.querySelector('.shipping-fee-truncated');
                if (truncatedSpan && truncatedSpan.dataset.fullText) {
                    // エスケープされた改行コード（\\n）を通常の改行（\n）に戻す
                    beforeShippingFee = truncatedSpan.dataset.fullText.replace(/\\n/g, '\n');
                } else {
                    const cell = firstRow.querySelector('td[data-field="shipping_fee"]');
                    if (cell) {
                        const cellText = cell.textContent.trim();
                        beforeShippingFee = cellText === '-' ? '' : cellText;
                    }
                }
            }
        }
        // --- 2026/06/04【ここまで追加】 ---

        const newRow = document.createElement('tr');
        newRow.className = 'table-warning';
        newRow.setAttribute('data-id', 'new');
        newRow.innerHTML = `
            <td class="text-muted period-year-${this.rowIndex}">自動算出</td>
            <td><input type="text" class="form-control form-control-sm date-input" name="new_effective_year_month_${this.rowIndex}" form="productForm" placeholder="YYYY/MM" required data-row-index="${this.rowIndex}"></td>
            <td><input type="text" class="form-control form-control-sm" name="new_wholesale_price_${this.rowIndex}" form="productForm" placeholder="仕切価格"></td>
            <td><input type="text" class="form-control form-control-sm" name="new_kenren_price_${this.rowIndex}" form="productForm" placeholder="県連価格"></td>
            <td><input type="text" class="form-control form-control-sm" name="new_retail_price_${this.rowIndex}" form="productForm" placeholder="参考小売価格"></td>
            <td><textarea class="form-control form-control-sm" name="new_shipping_fee_${this.rowIndex}" form="productForm" placeholder="送料">${beforeShippingFee}</textarea></td>
            <td class="text-muted gross-margin-${this.rowIndex}">自動算定</td>
            <td class="text-muted">自動算出</td>
            <td><input type="text" class="form-control form-control-sm" name="new_revision_reason_${this.rowIndex}" form="productForm" placeholder="改定理由"></td>
            <td><input type="text" class="form-control form-control-sm" name="new_memo_${this.rowIndex}" form="productForm" placeholder="メモ"></td>
            <td><button type="button" class="btn btn-sm btn-outline-secondary" data-action="remove-new-row">取消</button></td>
        `;
        tbody.insertBefore(newRow, tbody.firstChild);

        // 新規行の最初の入力フィールドにフォーカス
        const firstInput = newRow.querySelector('input');
        if (firstInput) {
            firstInput.focus();
        }

        this.rowIndex++;
        this.updateAddButtonState();
    }

    // 新規行削除機能
    removeNewRow(button) {
        const row = button.closest('tr');
        row.remove();
        this.updateAddButtonState();
    }

    // ボタン状態更新
    updateAddButtonState() {
        const addButton = document.getElementById('addPriceRowBtn');
        const tbody = this.querySelector('#priceHistoryTable tbody');
        const hasNewRow = tbody && tbody.querySelector('tr[data-id="new"]');

        if (addButton) {
            if (hasNewRow) {
                addButton.textContent = '編集中';
                addButton.disabled = true;
                addButton.classList.remove('btn-outline-primary');
                addButton.classList.add('btn-secondary');
            } else {
                addButton.textContent = '新規追加';
                addButton.disabled = false;
                addButton.classList.remove('btn-secondary');
                addButton.classList.add('btn-outline-primary');
            }
        }
    }



    // 削除マーク機能（standalone版と同じ）
    markForDeletion(button) {
        const row = button.closest('tr');
        const deleteFlag = row.querySelector('.delete-flag');
        const historyId = row.dataset.id;

        if (row.classList.contains('marked-for-deletion')) {
            // 削除マークを解除
            row.classList.remove('marked-for-deletion');
            row.style.backgroundColor = '';
            row.style.textDecoration = '';
            button.textContent = '削除';
            button.className = 'btn btn-sm btn-outline-danger delete-btn';
            deleteFlag.value = 'false';
            this.updateDeleteFlag(historyId, 'false');
        } else {
            // 削除マークを付与
            row.classList.add('marked-for-deletion');
            row.style.backgroundColor = '#ffebee';
            row.style.textDecoration = 'line-through';
            button.textContent = '取消';
            button.className = 'btn btn-sm btn-secondary delete-btn';
            deleteFlag.value = 'true';
            this.updateDeleteFlag(historyId, 'true');
        }
    }

    // 削除フラグをフォームに反映
    updateDeleteFlag(historyId, value) {
        const form = document.getElementById('productForm');
        const inputName = `delete_${historyId}`;

        // 既存のhidden inputを削除
        const existingInput = form.querySelector(`input[name="${inputName}"]`);
        if (existingInput) {
            existingInput.remove();
        }

        // 新しいhidden inputを追加
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = inputName;
        hiddenInput.value = value;
        form.appendChild(hiddenInput);
    }

    // インライン編集開始
    startInlineEdit(cell) {
        if (this.mode === 'approval' || cell.querySelector('input, textarea')) return; // 承認モードまたは既に編集中

        const originalValue = cell.textContent.trim();
        const field = cell.dataset.field;
        const historyId = cell.dataset.historyId;

        let inputElement;

        // 送料フィールドの場合はテキストエリアを使用
        if (field === 'shipping_fee') {
            inputElement = document.createElement('textarea');
            inputElement.rows = 2;
        } else {
            inputElement = document.createElement('input');
            inputElement.type = 'text';
        }

        inputElement.className = 'form-control form-control-sm';

        // 県連価格が自動計算（緑色）の場合は空のフォームにする
        if (field === 'kenren_price' && cell.style.color === 'green') {
            inputElement.value = '';
        } else {
            inputElement.value = originalValue;
        }

        inputElement.name = `edit_${field}_${historyId}`;
        inputElement.setAttribute('form', 'productForm');

        cell.innerHTML = '';
        cell.appendChild(inputElement);
        inputElement.focus();
        if (inputElement.select) inputElement.select();

        // Enterキーまたはフォーカス離脱で編集終了
        const finishEdit = () => {
            const newValue = inputElement.value.trim();

            // 価格フィールドの場合はカンマ区切りでフォーマット
            let displayValue = newValue;
            if ((field === 'wholesale_price' || field === 'kenren_price' || field === 'retail_price') && newValue) {
                displayValue = this.formatPrice(newValue);
            }

            cell.textContent = displayValue;

            // フォームにhidden inputを追加/更新（元の値で保存）
            this.updateFormInput(field, historyId, newValue);

            // 県連価格を手動入力した場合は黒色で表示
            if (field === 'kenren_price' && newValue) {
                cell.style.color = 'black';
                cell.style.fontWeight = 'normal';
            }

            // 仕切価格が変更された場合は県連価格を再計算
            if (field === 'wholesale_price') {
                this.updateKenrenPrice(historyId, newValue);
            }
        };

        inputElement.addEventListener('blur', finishEdit);
        inputElement.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && field !== 'shipping_fee') { // 送料以外でEnterキー
                e.preventDefault();
                finishEdit();
            } else if (e.key === 'Escape') {
                cell.textContent = originalValue;
            }
        });
    }

    // フォームにhidden inputを追加/更新
    updateFormInput(field, historyId, value) {
        const form = document.getElementById('productForm');
        const inputName = `edit_${field}_${historyId}`;

        // 既存のhidden inputを削除
        const existingInput = form.querySelector(`input[name="${inputName}"]`);
        if (existingInput) {
            existingInput.remove();
        }

        // 新しいhidden inputを追加（空文字列も追加）
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = inputName;
        hiddenInput.value = value;
        form.appendChild(hiddenInput);
    }

    // 県連価格の再計算
    updateKenrenPrice(historyId, wholesalePrice) {
        const row = this.querySelector(`tr[data-id="${historyId}"]`);
        if (!row) return;

        const kenrenCell = row.querySelector('.kenren-price-cell');
        if (!kenrenCell) return;

        // 新しい計算方式：仕切価格 ÷ 粗利率（デフォルト0.90）
        try {
            if (wholesalePrice && wholesalePrice !== '都度見積') {
                const price = parseFloat(wholesalePrice.replace(/,/g, ''));
                const defaultMarginRate = 0.90; // デフォルト粗利率
                const calculated = price / defaultMarginRate;
                // 1円の位を四捨五入（10円単位）
                const rounded = Math.round(calculated / 10) * 10;
                kenrenCell.textContent = rounded.toLocaleString();
                // 自動計算の場合は緑色で表示
                kenrenCell.style.color = 'green';
                kenrenCell.style.fontWeight = 'bold';
            } else {
                kenrenCell.textContent = '都度見積';
                kenrenCell.style.color = 'green';
                kenrenCell.style.fontWeight = 'bold';
            }
        } catch (e) {
            kenrenCell.textContent = '都度見積';
            kenrenCell.style.color = 'green';
            kenrenCell.style.fontWeight = 'bold';
        }
    }

    // 承認画面用のヘルパーメソッド
    getCellClass(history, field, isDiffRow) {
        let classes = [];

        if (this.mode !== 'approval' && this.editable && history.is_editable) {
            classes.push('editable-cell');
        }

        if (isDiffRow && history.diff_flags && history.diff_flags[field]) {
            classes.push('text-danger fw-bold');
        }

        return classes.join(' ');
    }

    getCellAttributes(history, field) {
        if (this.mode === 'approval' || !this.editable || !history.is_editable) {
            return '';
        }
        return `data-field="${field}" data-history-id="${history.id}"`;
    }

    getKenrenPriceStyle(history) {
        if (this.isAutoCalculated(history)) {
            return 'color: green; font-weight: bold;';
        }
        return '';
    }

    getKenrenPriceDisplay(history) {
        if (history.kenren_price) {
            return history.kenren_price;
        }
        return history.kenren_price_display || '都度見積';
    }

    getActionCell(history) {
        if (!history.is_editable) {
            return '<span class="text-muted">編集不可</span>';
        }
        return `
            <button type="button" class="btn btn-sm btn-outline-danger delete-btn" data-action="mark-delete">削除</button>
            <input type="hidden" class="delete-flag" value="false">
        `;
    }

    // 粗利率の表示値を取得（DBの値を正しく％表示に変換）
    getGrossMarginDisplay(history) {
        console.log('getGrossMarginDisplay input:', {
            gross_margin_rate: history.gross_margin_rate,
            type: typeof history.gross_margin_rate,
            historyId: history.id
        });

        if (history.gross_margin_rate !== null && history.gross_margin_rate !== undefined && history.gross_margin_rate !== '') {
            // 数値の場合は％表示に変換
            const rate = parseFloat(history.gross_margin_rate);
            if (!isNaN(rate)) {
                const result = window.GrossMarginUtils.formatGrossMarginRate(rate);
                console.log('Converted to percentage:', result);
                return result;
            }
            console.log('Returning raw value:', history.gross_margin_rate);
            return history.gross_margin_rate;
        }
        console.log('Returning default: 自動算出');
        return '自動算出';
    }

    // 自動計算かどうかを判定
    isAutoCalculated(history) {
        return !history.kenren_price || history.kenren_price === null;
    }

    // 送料の改行表示用フォーマット（3行制限付き）
    formatShippingFee(value) {
        if (!value || value === '-') {
            return value;
        }

        // 改行コードを正規化（\r\n → \n）
        const normalizedValue = value.replace(/\r\n/g, '\n');
        const lines = normalizedValue.split('\n');

        // 末尾の連続した空行のみ除去
        while (lines.length > 0 && lines[lines.length - 1].trim() === '') {
            lines.pop();
        }

        if (lines.length > 3) {
            // 3行を超える場合は省略表示
            const truncated = lines.slice(0, 3);
            truncated[2] = truncated[2] + '...';
            const displayText = truncated.join('<br>');
            return `<span class="shipping-fee-truncated" style="cursor: pointer; color: #0066cc;" data-full-text="${this.escapeForAttribute(normalizedValue)}">${displayText}</span>`;
        } else {
            // 3行以下はそのまま表示
            return lines.join('<br>');
        }
    }

    // 属性値用エスケープ
    escapeForAttribute(text) {
        return text.replace(/'/g, '&#39;').replace(/"/g, '&quot;').replace(/\n/g, '\\n');
    }

    // 価格をカンマ区切りでフォーマット
    formatPrice(value) {
        try {
            if (value === null || value === undefined || value === '') {
                return '-';
            }

            // 「都度見積」などの文字列はそのまま返す
            if (typeof value === 'string' && isNaN(value.replace(/,/g, ''))) {
                return value;
            }

            // 数値に変換してカンマ区切り
            const numValue = parseFloat(String(value).replace(/,/g, ''));
            if (isNaN(numValue)) {
                return value;
            }

            return numValue.toLocaleString();
        } catch (e) {
            return value || '-';
        }
    }

    // 年度算出と粗利率更新
    updatePeriodAndMargin(rowIndex) {
        console.log('updatePeriodAndMargin called with rowIndex:', rowIndex);
        const dateInput = this.querySelector(`input[name="new_effective_year_month_${rowIndex}"]`);
        const periodCell = this.querySelector(`.period-year-${rowIndex}`);
        const marginCell = this.querySelector(`.gross-margin-${rowIndex}`);

        console.log('Elements found:', {
            dateInput: !!dateInput,
            periodCell: !!periodCell,
            marginCell: !!marginCell,
            dateValue: dateInput?.value
        });

        if (!dateInput || !periodCell || !marginCell) return;

        const dateValue = dateInput.value.trim();
        if (!dateValue.match(/^\d{4}\/\d{1,2}$/)) {
            console.log('Date format invalid:', dateValue);
            periodCell.textContent = '自動算出';
            marginCell.textContent = '自動算定';
            return;
        }

        try {
            const [year, month] = dateValue.split('/').map(Number);
            const periodYear = month >= 4 ? year : year - 1;

            console.log('Calculated period year:', periodYear);
            periodCell.textContent = `${periodYear}年度`;

            // 粗利率を取得
            this.fetchGrossMargin(periodYear, marginCell);
        } catch (e) {
            console.log('Error in updatePeriodAndMargin:', e);
            periodCell.textContent = '自動算出';
            marginCell.textContent = '自動算定';
        }
    }

    // 粗利率を取得（APIから取得）
    fetchGrossMargin(periodYear, marginCell) {
        const pathParts = window.location.pathname.split('/').filter(p => p);
        // products/products/59/ または products/products/59/submit-approval/ から59を取得
        let productId = null;
        for (let i = 0; i < pathParts.length; i++) {
            if (pathParts[i] === 'products' && pathParts[i + 1] === 'products' && pathParts[i + 2]) {
                productId = pathParts[i + 2];
                break;
            }
        }

        fetch(`/products/api/gross-margins/${productId}/`)
            .then(response => response.json())
            .then(margins => {
                // n年度以下で最新の粗利率を取得
                const applicableMargin = margins
                    .filter(m => m.period_year <= periodYear)
                    .sort((a, b) => b.period_year - a.period_year)[0];

                if (applicableMargin) {
                    const profitDisplay = window.GrossMarginUtils.formatGrossMarginRate(applicableMargin.gross_margin_rate);
                    marginCell.textContent = profitDisplay;
                } else {
                    marginCell.textContent = '10.0%'; // デフォルト
                }
            })
            .catch(error => {
                console.error('Error fetching gross margin:', error);
                marginCell.textContent = '10.0%'; // エラー時のデフォルト
            });
    }

    // 外部から呼び出し可能なメソッド（既存のJavaScriptとの互換性）
    addNewRow() {
        this.addPriceRow();
    }
}

// Webコンポーネントを登録
customElements.define('price-history-component', PriceHistoryComponent);

// 既存のグローバル関数との互換性を保持
window.addPriceRow = function () {
    console.log('addPriceRow called');
    const component = document.querySelector('price-history-component');

    if (!component) {
        console.log('Component not found');
        return;
    }

    // 既に新規行があるかチェック
    const tbody = component.querySelector('#priceHistoryTable tbody');
    const existingNewRow = tbody ? tbody.querySelector('tr[data-id="new"]') : null;

    console.log('Existing new row:', existingNewRow);

    if (existingNewRow) {
        console.log('New row already exists, focusing...');
        // 既存の新規行にフォーカス
        const firstInput = existingNewRow.querySelector('input');
        if (firstInput) {
            firstInput.focus();
        }
        alert('新規行は1つまでしか追加できません。');
        return;
    }

    console.log('Adding new row...');
    // 新規行を追加
    component.addPriceRow();
};