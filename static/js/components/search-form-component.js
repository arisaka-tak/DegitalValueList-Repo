class SearchFormComponent extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const searchQuery = this.getAttribute('search-query') || '';
        const placeholder = this.getAttribute('placeholder') || '検索';
        const searchUrl = this.getAttribute('search-url') || '';
        const clearUrl = this.getAttribute('clear-url') || '';

        this.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <form method="GET" class="row g-3">
                        <div class="col-md-8">
                            <input type="text" class="form-control" name="search" 
                                   value="${this.escapeHtml(searchQuery)}" 
                                   placeholder="${this.escapeHtml(placeholder)}">
                        </div>
                        <div class="col-md-4">
                            <button type="submit" class="btn btn-primary">検索</button>
                            <a href="${this.escapeHtml(clearUrl)}" class="btn btn-outline-secondary">クリア</a>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

customElements.define('search-form-component', SearchFormComponent);