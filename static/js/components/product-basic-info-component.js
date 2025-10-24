class ProductBasicInfoComponent extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const productData = JSON.parse(this.getAttribute('product-data') || '{}');
        const formData = JSON.parse(this.getAttribute('form-data') || '{}');
        const isEditable = this.getAttribute('editable') === 'true';
        const isNew = this.getAttribute('is-new') === 'true';
        const diffFlags = JSON.parse(this.getAttribute('diff-flags') || '{}');

        this.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label text-muted">商品番号</label>
                        ${this.renderProductNumber(productData, isNew)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_product_code">商品コード</label>
                        ${this.renderField('product_code', productData, formData, isEditable, diffFlags)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_product_name">商品名</label>
                        ${this.renderField('product_name', productData, formData, isEditable, diffFlags)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_livestock_type">畜種</label>
                        ${this.renderField('livestock_type', productData, formData, isEditable, diffFlags)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_category">分類</label>
                        ${this.renderField('category', productData, formData, isEditable, diffFlags)}
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label text-muted">　</label>
                        <div class="form-control-plaintext">　</div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_manufacturer">メーカー</label>
                        ${this.renderField('manufacturer', productData, formData, isEditable, diffFlags)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_model_number">型式</label>
                        ${this.renderField('model_number', productData, formData, isEditable, diffFlags)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_specification">規格</label>
                        ${this.renderField('specification', productData, formData, isEditable, diffFlags)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_shipping_unit">発送単位</label>
                        ${this.renderField('shipping_unit', productData, formData, isEditable, diffFlags)}
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label" for="id_shipping_fee">送料</label>
                        ${this.renderField('shipping_fee', productData, formData, isEditable, diffFlags)}
                    </div>
                </div>
            </div>

            <div class="mb-3">
                <label class="form-label" for="id_remarks">備考</label>
                ${this.renderTextareaField('remarks', productData, formData, isEditable, diffFlags)}
            </div>
        `;
    }

    renderProductNumber(productData, isNew) {
        if (isNew) {
            return '<div class="form-control-plaintext text-muted">保存時に自動採番</div>';
        } else if (productData.product_number > 0) {
            return `<div class="form-control-plaintext fw-bold">${productData.product_number}</div>`;
        } else {
            return `<div class="form-control-plaintext text-success fw-bold">新規作成 (仮${productData.product_number})</div>`;
        }
    }

    renderField(fieldName, productData, formData, isEditable, diffFlags) {
        const value = productData[fieldName] || '';
        // フォームデータがある場合はそれを優先、なければ商品データを使用
        const formValue = formData[fieldName] !== undefined ? formData[fieldName] : value;
        const isDiff = diffFlags[fieldName] || false;
        
        if (isEditable) {
            return `<input type="text" class="form-control" id="id_${fieldName}" name="${fieldName}" value="${this.escapeHtml(formValue)}" form="productForm">`;
        } else {
            const diffClass = isDiff ? ' text-danger fw-bold' : '';
            const displayValue = value || '-';
            return `<div class="form-control-plaintext${diffClass}">${this.escapeHtml(displayValue)}</div>`;
        }
    }

    renderTextareaField(fieldName, productData, formData, isEditable, diffFlags) {
        const value = productData[fieldName] || '';
        // フォームデータがある場合はそれを優先、なければ商品データを使用
        const formValue = formData[fieldName] !== undefined ? formData[fieldName] : value;
        const isDiff = diffFlags[fieldName] || false;
        
        if (isEditable) {
            return `<textarea class="form-control" id="id_${fieldName}" name="${fieldName}" rows="3" form="productForm">${this.escapeHtml(formValue)}</textarea>`;
        } else {
            const diffClass = isDiff ? ' text-danger fw-bold' : '';
            const displayValue = value || '-';
            return `<div class="form-control-plaintext${diffClass}">${this.escapeHtml(displayValue)}</div>`;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

customElements.define('product-basic-info-component', ProductBasicInfoComponent);