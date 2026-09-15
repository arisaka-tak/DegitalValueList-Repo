/**
 * 粗利率計算の共通関数
 */

/**
 * 粗利率を計算（仕切価格÷県連価格）
 * @param {number} wholesalePrice 仕切価格
 * @param {number} kenrenPrice 県連価格
 * @returns {number|null} 粗利率（小数点第2位まで切り捨て）
 */
function calculateGrossMarginRate(wholesalePrice, kenrenPrice) {
    try {
        if (kenrenPrice > 0) {
            const marginRate = wholesalePrice / kenrenPrice;
            // 小数点第2位まで、3位以下切り捨て
            return Math.floor(marginRate * 100) / 100;
        }
    } catch (e) {
        // エラー時はnullを返す
    }
    return null;
}

/**
 * 粗利率を％表示に変換（1-粗利率）
 * @param {number} marginRate 粗利率
 * @returns {string} ％表示（例：10.0%）
 */
function formatGrossMarginRate(marginRate) {
    try {
        if (marginRate !== null && marginRate !== undefined) {
            const profitRate = (1 - marginRate) * 100;
            return profitRate.toFixed(1) + '%';
        }
    } catch (e) {
        // エラー時は'-'を返す
    }
    return '-';
}

/**
 * 県連価格を計算（仕切価格÷粗利率）
 * @param {number} wholesalePrice 仕切価格
 * @param {number} marginRate 粗利率
 * @returns {number|null} 県連価格（10円単位四捨五入）
 */
function calculateKenrenPrice(wholesalePrice, marginRate) {
    try {
        if (marginRate > 0) {
            const calculated = wholesalePrice / marginRate;
            // 10円単位で四捨五入
            return Math.round(calculated / 10) * 10;
        }
    } catch (e) {
        // エラー時はnullを返す
    }
    return null;
}

// グローバルに公開
window.GrossMarginUtils = {
    calculateGrossMarginRate,
    formatGrossMarginRate,
    calculateKenrenPrice
};