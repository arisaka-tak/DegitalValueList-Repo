class PriceHistoryComponent extends HTMLElement {
    constructor() {
        super();
        this.rowIndex = 0;
    }

    connectedCallback() {
        this.mode = this.getAttribute('mode') || 'edit';
        this.showDiff = this.getAttribute('show-diff') === 'true';
        this.editable = this.getAttribute('editable') !== 'false';
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
                            <th>粗利率</th>
                            ${!isApprovalMode ? '<th>改定額</th>' : ''}
                            <th>改定理由</th>
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
        const isApprovalMode = this.mode === 'approval';
        
        return histories.map(history => {
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
            
            return `
                <tr data-id="${history.id}" class="${rowClass}" style="${rowStyle}">
                    <td>${history.period_year}年度</td>
                    <td>${history.effective_year_month}</td>
                    <td class="${this.getCellClass(history, 'wholesale_price', isDiffRow)}" ${this.getCellAttributes(history, 'wholesale_price')}>${this.formatPrice(history.wholesale_price)}</td>
                    <td class="kenren-price-cell ${this.getCellClass(history, 'kenren_price', isDiffRow)}" ${this.getCellAttributes(history, 'kenren_price')} style="${this.getKenrenPriceStyle(history)}">${this.formatPrice(this.getKenrenPriceDisplay(history))}</td>
                    <td>${this.getGrossMarginDisplay(history)}</td>
                    ${!isApprovalMode ? `<td>${history.revision_amount !== null && history.revision_amount !== undefined ? history.revision_amount : '自動算出'}</td>` : ''}
                    <td class="${this.getCellClass(history, 'revision_reason', isDiffRow)}" ${this.getCellAttributes(history, 'revision_reason')}>${history.revision_reason || (isDiffRow ? '' : '-')}</td>
                    ${!isApprovalMode ? `<td>${this.getActionCell(history)}</td>` : ''}
                </tr>
            `;
        }).join('');
    }

    setupEventListeners() {
        if (this.mode === 'approval') {
            return; // 承認モードではイベントリスナーを設定しない
        }
        
        // イベント委譲でボタンクリックを処理
        this.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            
            switch(action) {
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
    }

    // 新規行追加機能
    addPriceRow() {
        if (this.mode === 'approval') return; // 承認モードでは追加不可
        
        const tbody = this.querySelector('#priceHistoryTable tbody');
        const newRow = document.createElement('tr');
        newRow.className = 'table-warning';
        newRow.setAttribute('data-id', 'new');
        newRow.innerHTML = `
            <td class="text-muted">自動算出</td>
            <td><input type="text" class="form-control form-control-sm" name="new_effective_year_month_${this.rowIndex}" form="productForm" placeholder="YYYY/MM" required></td>
            <td><input type="text" class="form-control form-control-sm" name="new_wholesale_price_${this.rowIndex}" form="productForm" placeholder="仕切価格"></td>
            <td><input type="text" class="form-control form-control-sm" name="new_kenren_price_${this.rowIndex}" form="productForm" placeholder="県連価格"></td>
            <td class="text-muted">自動算出</td>
            <td class="text-muted">自動算出</td>
            <td><input type="text" class="form-control form-control-sm" name="new_revision_reason_${this.rowIndex}" form="productForm" placeholder="改定理由"></td>
            <td><button type="button" class="btn btn-sm btn-outline-secondary" data-action="remove-new-row">取消</button></td>
        `;
        tbody.insertBefore(newRow, tbody.firstChild);
        this.rowIndex++;
    }

    // 新規行削除機能（standalone版と同じ）
    removeNewRow(button) {
        button.closest('tr').remove();
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
        if (this.mode === 'approval' || cell.querySelector('input')) return; // 承認モードまたは既に編集中
        
        const originalValue = cell.textContent.trim();
        const field = cell.dataset.field;
        const historyId = cell.dataset.historyId;
        
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control form-control-sm';
        
        // 県連価格が自動計算（緑色）の場合は空のフォームにする
        if (field === 'kenren_price' && cell.style.color === 'green') {
            input.value = '';
        } else {
            input.value = originalValue;
        }
        
        input.name = `edit_${field}_${historyId}`;
        input.setAttribute('form', 'productForm');
        
        cell.innerHTML = '';
        cell.appendChild(input);
        input.focus();
        input.select();
        
        // Enterキーまたはフォーカス離脱で編集終了
        const finishEdit = () => {
            const newValue = input.value.trim();
            
            // 価格フィールドの場合はカンマ区切りでフォーマット
            let displayValue = newValue || originalValue;
            if ((field === 'wholesale_price' || field === 'kenren_price') && newValue) {
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
        
        input.addEventListener('blur', finishEdit);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
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
        
        // 新しいhidden inputを追加
        if (value) {
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = inputName;
            hiddenInput.value = value;
            form.appendChild(hiddenInput);
        }
    }
    
    // 県連価格の再計算
    updateKenrenPrice(historyId, wholesalePrice) {
        const row = this.querySelector(`tr[data-id="${historyId}"]`);
        if (!row) return;
        
        const kenrenCell = row.querySelector('.kenren-price-cell');
        if (!kenrenCell) return;
        
        // 簡易的な計算（実際の粗利率は不明なので1.1を仮定）
        try {
            if (wholesalePrice && wholesalePrice !== '都度見積') {
                const price = parseFloat(wholesalePrice.replace(/,/g, ''));
                const calculated = Math.floor(price * 1.1);
                kenrenCell.textContent = calculated.toLocaleString();
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
    
    // 粗利率の表示値を取得（1.1 → 10%）
    getGrossMarginDisplay(history) {
        if (history.gross_margin_rate !== null && history.gross_margin_rate !== undefined && history.gross_margin_rate !== '') {
            const rate = parseFloat(history.gross_margin_rate);
            if (rate === 0.0) {
                return '0.0%';
            }
            // 粗利率を計算（(1.1 - 1) * 100 = 10%）
            const profitRate = (rate - 1) * 100;
            return profitRate.toFixed(1) + '%';
        }
        return '自動算出';
    }
    
    // 自動計算かどうかを判定
    isAutoCalculated(history) {
        return !history.kenren_price || history.kenren_price === null;
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
    
    // 外部から呼び出し可能なメソッド（既存のJavaScriptとの互換性）
    addNewRow() {
        this.addPriceRow();
    }
}

// Webコンポーネントを登録
customElements.define('price-history-component', PriceHistoryComponent);

// 既存のグローバル関数との互換性を保持
window.addPriceRow = function() {
    const component = document.querySelector('price-history-component');
    if (component) {
        component.addNewRow();
    }
};