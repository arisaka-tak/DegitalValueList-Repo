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
        const errorFields = JSON.parse(this.getAttribute('error-fields') || '[]');
        const livestockTypes = JSON.parse(this.getAttribute('livestock-types') || '[]');
        const categories = JSON.parse(this.getAttribute('categories') || '[]');
        const manufacturers = JSON.parse(this.getAttribute('manufacturers') || '[]');

        this.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">商品番号</label>
                        ${this.renderProductNumber(productData, isNew)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_product_name">商品名</label>
                        ${this.renderTextareaField('product_name', productData, formData, isEditable, diffFlags, errorFields, true)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_livestock_type">畜種</label>
                        ${this.renderSelectField('livestock_type', productData, formData, isEditable, diffFlags, errorFields, livestockTypes)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_category">分類</label>
                        ${this.renderSelectField('category', productData, formData, isEditable, diffFlags, errorFields, categories)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_shipping_fee">送料</label>
                        ${this.renderTextareaField('shipping_fee', productData, formData, isEditable, diffFlags, errorFields)}
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label" for="id_product_code">商品コード</label>
                        ${this.renderField('product_code', productData, formData, isEditable, diffFlags, errorFields)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_manufacturer">メーカー</label>
                        ${this.renderManufacturerField('manufacturer', productData, formData, isEditable, diffFlags, errorFields, manufacturers)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_model_number">型式</label>
                        ${this.renderField('model_number', productData, formData, isEditable, diffFlags, errorFields)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_specification">規格</label>
                        ${this.renderTextareaField('specification', productData, formData, isEditable, diffFlags, errorFields)}
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="id_shipping_unit">発送単位</label>
                        ${this.renderField('shipping_unit', productData, formData, isEditable, diffFlags, errorFields)}
                    </div>
                </div>
            </div>

            <div class="mb-3">
                <label class="form-label" for="id_remarks">備考</label>
                ${this.renderTextareaField('remarks', productData, formData, isEditable, diffFlags, errorFields)}
            </div>
        `;
    }

    renderProductNumber(productData, isNew) {
        if (isNew) {
            return '<div class="form-control text-muted" style="background-color: #f8f9fa; border: 1px solid #dee2e6;">保存時に自動採番</div>';
        } else if (productData.product_number > 0) {
            return `<div class="form-control fw-bold" style="background-color: #f8f9fa; border: 1px solid #dee2e6;">${productData.product_number}</div>`;
        } else {
            return `<div class="form-control text-success fw-bold" style="background-color: #f8f9fa; border: 1px solid #dee2e6;">新規作成 (仮${productData.product_number})</div>`;
        }
    }

    renderField(fieldName, productData, formData, isEditable, diffFlags, errorFields) {
        const value = productData[fieldName] || '';
        // フォームデータがある場合はそれを優先、なければ商品データを使用
        const formValue = formData[fieldName] !== undefined ? formData[fieldName] : value;
        const isDiff = diffFlags[fieldName] || false;
        const hasError = errorFields.includes(fieldName);
        const isRequired = fieldName === 'product_name';
        
        if (isEditable) {
            const errorClass = hasError ? ' is-invalid' : '';
            const requiredStyle = isRequired ? ' style="border: 2px solid #0d6efd;"' : '';
            return `<input type="text" class="form-control${errorClass}" id="id_${fieldName}" name="${fieldName}" value="${this.escapeHtml(formValue)}"${requiredStyle}>`;
        } else {
            const diffClass = isDiff ? ' text-danger fw-bold' : '';
            const displayValue = value || '-';
            return `<div class="form-control-plaintext${diffClass}">${this.escapeHtml(displayValue)}</div>`;
        }
    }

    renderTextareaField(fieldName, productData, formData, isEditable, diffFlags, errorFields, isRequired = false) {
        const value = productData[fieldName] || '';
        // フォームデータがある場合はそれを優先、なければ商品データを使用
        const formValue = formData[fieldName] !== undefined ? formData[fieldName] : value;
        const isDiff = diffFlags[fieldName] || false;
        const hasError = errorFields.includes(fieldName);
        
        if (isEditable) {
            const errorClass = hasError ? ' is-invalid' : '';
            const requiredStyle = isRequired ? ' style="border: 2px solid #0d6efd;"' : '';
            return `<textarea class="form-control${errorClass}" id="id_${fieldName}" name="${fieldName}" rows="3"${requiredStyle}>${this.escapeHtml(formValue)}</textarea>`;
        } else {
            const diffClass = isDiff ? ' text-danger fw-bold' : '';
            const displayValue = value || '-';
            return `<div class="form-control-plaintext${diffClass}">${this.escapeHtml(displayValue).replace(/\n/g, '<br>')}</div>`;
        }
    }

    renderSelectField(fieldName, productData, formData, isEditable, diffFlags, errorFields, options) {
        const value = productData[fieldName] || '';
        const formValue = formData[fieldName] !== undefined ? formData[fieldName] : value;
        const isDiff = diffFlags[fieldName] || false;
        const hasError = errorFields.includes(fieldName);
        
        if (isEditable) {
            const errorClass = hasError ? ' is-invalid' : '';
            let optionsHtml = '<option value="">選択してください</option>';
            
            options.forEach(option => {
                const selected = formValue == option.id ? ' selected' : '';
                optionsHtml += `<option value="${option.id}"${selected}>${this.escapeHtml(option.name)}</option>`;
            });
            
            return `<select class="form-select${errorClass}" id="id_${fieldName}" name="${fieldName}">${optionsHtml}</select>`;
        } else {
            const diffClass = isDiff ? ' text-danger fw-bold' : '';
            // IDから名前を取得して表示
            const selectedOption = options.find(option => option.id == value);
            const displayValue = selectedOption ? selectedOption.name : (value || '-');
            return `<div class="form-control-plaintext${diffClass}">${this.escapeHtml(displayValue)}</div>`;
        }
    }

    renderManufacturerField(fieldName, productData, formData, isEditable, diffFlags, errorFields, manufacturers = []) {
        const value = productData[fieldName] || '';
        const formValue = formData[fieldName] !== undefined ? formData[fieldName] : value;
        const isDiff = diffFlags[fieldName] || false;
        const hasError = errorFields.includes(fieldName);
        
        if (isEditable) {
            const errorClass = hasError ? ' is-invalid' : '';
            // メーカーIDから名前を取得して表示する
            let displayName = 'メーカーを選択してください';
            if (formValue) {
                // メーカー名をAPIから取得するためのプレースホルダー
                displayName = `ID: ${formValue}`;
            }
            return `
                <div class="input-group">
                    <input type="text" class="form-control${errorClass}" id="id_${fieldName}_display" readonly placeholder="メーカーを選択してください" value="${displayName}">
                    <input type="hidden" id="id_${fieldName}" name="${fieldName}" value="${this.escapeHtml(formValue)}">
                    <button type="button" class="btn btn-outline-secondary" onclick="openManufacturerModal()">選択</button>
                </div>
            `;
        } else {
            const diffClass = isDiff ? ' text-danger fw-bold' : '';
            // IDから名前を取得して表示
            const selectedManufacturer = manufacturers.find(m => m.id == value);
            const displayValue = selectedManufacturer ? selectedManufacturer.name : (value || '-');
            return `<div class="form-control-plaintext${diffClass}">${this.escapeHtml(displayValue)}</div>`;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // メーカー選択後のコールバック
    setManufacturer(id, name) {
        const hiddenInput = document.getElementById('id_manufacturer');
        const displayInput = document.getElementById('id_manufacturer_display');
        if (hiddenInput && displayInput) {
            hiddenInput.value = id;
            displayInput.value = name;
        }
    }
    
    // コンポーネントがレンダリングされた後にメーカー名を取得
    connectedCallback() {
        this.render();
        // メーカー名を非同期で取得
        setTimeout(() => this.loadManufacturerName(), 100);
    }
    
    async loadManufacturerName() {
        const manufacturerId = document.getElementById('id_manufacturer')?.value;
        const displayInput = document.getElementById('id_manufacturer_display');
        
        if (manufacturerId && displayInput && manufacturerId !== '') {
            try {
                const response = await fetch('/products/api/manufacturers/');
                const manufacturers = await response.json();
                const manufacturer = manufacturers.find(m => m.id == manufacturerId);
                if (manufacturer) {
                    displayInput.value = manufacturer.name;
                }
            } catch (error) {
                console.error('Failed to load manufacturer name:', error);
            }
        }
    }
    
    async loadManufacturerNameForDisplay(fieldName, manufacturerId) {
        try {
            const response = await fetch('/products/api/manufacturers/');
            const manufacturers = await response.json();
            const manufacturer = manufacturers.find(m => m.id == manufacturerId);
            if (manufacturer) {
                const displayElement = document.getElementById(`display_${fieldName}`);
                if (displayElement) {
                    displayElement.textContent = manufacturer.name;
                }
            }
        } catch (error) {
            console.error('Failed to load manufacturer name for display:', error);
        }
    }
}

customElements.define('product-basic-info-component', ProductBasicInfoComponent);

// グローバル関数
function openManufacturerModal() {
    const modal = new bootstrap.Modal(document.getElementById('manufacturerModal'));
    modal.show();
}

function selectManufacturer(id, name) {
    const component = document.querySelector('product-basic-info-component');
    if (component) {
        component.setManufacturer(id, name);
    }
    const modal = bootstrap.Modal.getInstance(document.getElementById('manufacturerModal'));
    modal.hide();
}