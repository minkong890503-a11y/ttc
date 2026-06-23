// 결산분석 화면 스크립트 v3
// 기존 HTML 요약 영역 제거 + 새 요약 카드를 흰색 박스로 렌더링

document.addEventListener("DOMContentLoaded", function () {
    bindAnalyticsButtons();
    loadAnalytics();
});

function bindAnalyticsButtons() {
    document.querySelectorAll("button, a").forEach((button) => {
        const text = (button.textContent || "").trim();
        if (text === "조회" || text === "새로고침") {
            button.addEventListener("click", function (event) {
                event.preventDefault();
                loadAnalytics();
            });
        }
    });
}

function getFilterValue(selectors, fallback = "") {
    for (const selector of selectors) {
        const el = document.querySelector(selector);
        if (el && el.value) return el.value;
    }
    return fallback;
}

function getFilters() {
    const today = new Date();
    const monthFallback = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
    const dateFallback = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

    return {
        month: getFilterValue(["#month", "#monthFilter", "#filterMonth", "input[type='month']", "select[name='month']", "input[name='month']"], monthFallback),
        date: getFilterValue(["#date", "#selectedDate", "#filterDate", "input[type='date']", "input[name='date']"], dateFallback),
        basis: getFilterValue(["#basis", "#analysisBasis", "select[name='basis']", "input[name='basis']:checked"], "calendar"),
        average: getFilterValue(["#average", "#averageBasis", "select[name='average']", "input[name='average']:checked"], "all")
    };
}

async function loadAnalytics() {
    const filters = getFilters();

    try {
        const summaryResponse = await fetch(`/api/analytics/summary_v2?month=${encodeURIComponent(filters.month)}&date=${encodeURIComponent(filters.date)}&basis=${encodeURIComponent(filters.basis)}&average=${encodeURIComponent(filters.average)}`);
        const summary = await summaryResponse.json();

        if (!summaryResponse.ok || summary.ok === false) {
            showAnalyticsError(summary.error || "요약 데이터를 불러오지 못했습니다.");
            return;
        }

        removeLegacySummaryBlocks();
        renderSummary(summary);
        await renderTrendCharts(filters);
        await renderWeekdayCharts(filters);
    } catch (error) {
        console.error(error);
        showAnalyticsError("결산분석 데이터를 불러오는 중 오류가 발생했습니다.");
    }
}

function removeLegacySummaryBlocks() {
    const titles = ["오늘 요약", "특정일 요약", "이번달 누적", "비교 상태"];

    document.querySelectorAll("h1, h2, h3, h4, strong, b").forEach((heading) => {
        const title = (heading.textContent || "").trim();
        if (!titles.includes(title)) return;
        if (heading.closest(".analytics-summary-grid-fixed")) return;

        let target = heading.closest(".summary-card, .card, .panel, section");
        if (!target) target = heading.parentElement;
        if (!target) return;

        const text = target.textContent || "";
        const isSummary =
            text.includes("총내원") ||
            text.includes("신환매출") ||
            text.includes("구환매출") ||
            text.includes("불러오는 중") ||
            text.includes("지난달") ||
            text.includes("평균");

        if (isSummary) target.remove();
    });
}

function getOrCreateSummaryGrid() {
    let grid = document.querySelector(".analytics-summary-grid-fixed");
    if (grid) return grid;

    const filterCard = findSectionByTitle("분석 필터") || document.querySelector(".card") || document.body;

    grid = document.createElement("div");
    grid.className = "analytics-summary-grid-fixed";
    filterCard.insertAdjacentElement("afterend", grid);
    return grid;
}

function showAnalyticsError(message) {
    removeLegacySummaryBlocks();
    const grid = getOrCreateSummaryGrid();
    grid.innerHTML = `<div class="summary-card"><div class="analytics-message">${escapeHtml(message)}</div></div>`;
}

function renderSummary(data) {
    const grid = getOrCreateSummaryGrid();
    grid.innerHTML = "";

    grid.appendChild(createNormalSummaryCard("오늘 요약", data.today));
    grid.appendChild(createNormalSummaryCard("특정일 요약", data.selected));
    grid.appendChild(createMonthCard("이번달 누적", data.month_cumulative));
    grid.appendChild(createComparisonCard("비교 상태", data.comparison));
}

function createNormalSummaryCard(title, item) {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `
        <h4 class="card-title">${escapeHtml(title)}</h4>
        ${summaryRow("날짜", formatDateWithWeekday(item.date, item.weekday))}
        ${summaryRow("총내원", `${formatNumber(item.total_visit_count)}명`)}
        ${summaryRow("신환매출", formatWon(item.new_customer_sales))}
        ${summaryRow("구환매출", formatWon(item.returning_customer_sales))}
        ${summaryRow("일일총매출", formatWon(item.total_daily_sales), true)}
        ${summaryRow("총지출", formatWon(item.total_expense))}
        ${summaryRow("결산", formatWon(item.closing_amount), true)}
    `;
    return card;
}

function createMonthCard(title, item) {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `
        <h4 class="card-title">${escapeHtml(title)}</h4>
        ${summaryRow("총내원", `${formatNumber(item.total_visit_count)}명`)}
        ${summaryRow("신환매출", formatWon(item.new_customer_sales))}
        ${summaryRow("구환매출", formatWon(item.returning_customer_sales))}
        ${summaryRow("월 누적매출", formatWon(item.total_daily_sales), true)}
        ${summaryRow("월 총지출", formatWon(item.total_expense))}
        ${summaryRow("월 결산", formatWon(item.closing_amount), true)}
    `;
    return card;
}

function createComparisonCard(title, comparison) {
    const weekday = comparison.today_weekday || "";
    const card = document.createElement("div");
    card.className = "summary-card comparison-card";
    card.innerHTML = `
        <h4 class="card-title">${escapeHtml(title)}</h4>
        <p class="comparison-basis">기준: 선택일(${weekday}요일) 기준</p>

        <div class="comparison-section">
            <div class="comparison-section-title">매출 비교</div>
            ${comparisonRow(`지난달 ${weekday}요일 평균 대비`, comparison.vs_lastmonth_weekday_sales, "원", comparison.vs_lastmonth_weekday_sales_direction)}
            ${comparisonRow("평균 매출 대비", comparison.vs_average_sales, "원", comparison.vs_average_sales_direction)}
        </div>

        <div class="comparison-section" style="margin-top: 12px;">
            <div class="comparison-section-title">방문 비교</div>
            ${comparisonRow(`지난달 ${weekday}요일 평균 대비`, comparison.vs_lastmonth_weekday_visit, "명", comparison.vs_lastmonth_weekday_visit_direction)}
            ${comparisonRow("평균 방문 대비", comparison.vs_average_visit, "명", comparison.vs_average_visit_direction)}
        </div>
    `;
    return card;
}

function summaryRow(label, value, highlight = false) {
    return `
        <div class="summary-row">
            <span class="summary-label">${escapeHtml(label)}</span>
            <span class="summary-value ${highlight ? "highlight" : ""}">${escapeHtml(value)}</span>
        </div>
    `;
}

function comparisonRow(label, value, unit, direction) {
    const number = Number(value || 0);
    const dir = direction || (number > 0 ? "up" : number < 0 ? "down" : "neutral");
    const symbol = dir === "up" ? "▲" : dir === "down" ? "▼" : "－";
    const absValue = Math.abs(number);

    return `
        <div class="summary-row">
            <span class="summary-label">${escapeHtml(label)}</span>
            <span class="summary-value ${dir}">${symbol} ${formatNumber(absValue)}${unit}</span>
        </div>
    `;
}

async function renderTrendCharts(filters) {
    const response = await fetch(`/api/analytics/trend?month=${encodeURIComponent(filters.month)}&basis=${encodeURIComponent(filters.basis)}&average=${encodeURIComponent(filters.average)}`);
    if (!response.ok) return;

    const data = await response.json();
    const section = findSectionByTitle("누적 선 그래프") || findSectionByTitle("실근무일");
    if (!section) return;

    renderChartGrid(section, data, "line");
}

async function renderWeekdayCharts(filters) {
    const response = await fetch(`/api/analytics/weekday?month=${encodeURIComponent(filters.month)}&average=${encodeURIComponent(filters.average)}`);
    if (!response.ok) return;

    const data = await response.json();
    const section = findSectionByTitle("요일별 막대 그래프") || findSectionByTitle("요일별");
    if (!section) return;

    renderChartGrid(section, data, "bar");
}

function findSectionByTitle(titleText) {
    const candidates = Array.from(document.querySelectorAll("section, .card, .panel, div"));
    return candidates.find((el) => {
        const h = el.querySelector("h1, h2, h3, h4");
        return h && h.textContent && h.textContent.includes(titleText);
    });
}

function renderChartGrid(section, data, chartType) {
    if (!data || !data.charts || !data.labels) return;

    const oldGrid = section.querySelector(".chart-grid");
    if (oldGrid) oldGrid.remove();

    const grid = document.createElement("div");
    grid.className = "chart-grid";
    section.appendChild(grid);

    Object.entries(data.charts).forEach(([key, chartData]) => {
        const card = document.createElement("div");
        card.className = "chart-card";

        const title = document.createElement("h4");
        title.textContent = chartData.title || key;

        const canvas = document.createElement("canvas");
        canvas.id = `chart-${chartType}-${key}`;

        card.appendChild(title);
        card.appendChild(canvas);
        grid.appendChild(card);

        drawChart(canvas, data.labels, chartData, chartType);
    });
}

function drawChart(canvas, labels, chartData, chartType) {
    if (!window.Chart) {
        canvas.parentElement.insertAdjacentHTML("beforeend", `<div class="analytics-message">Chart.js를 불러오지 못했습니다.</div>`);
        return;
    }

    const datasets = [];

    if (Array.isArray(chartData.current)) {
        datasets.push({
            label: "이번달",
            data: chartData.current,
            borderWidth: chartType === "line" ? 3 : 1,
            tension: 0.25,
            spanGaps: false
        });
    }

    if (Array.isArray(chartData.previous)) {
        datasets.push({
            label: "지난달",
            data: chartData.previous,
            borderWidth: 1,
            tension: 0.25,
            spanGaps: false
        });
    }

    if (Array.isArray(chartData.average)) {
        datasets.push({
            label: "평균",
            data: chartData.average,
            borderWidth: 1,
            borderDash: chartType === "line" ? [4, 4] : undefined,
            tension: 0.25,
            spanGaps: false
        });
    }

    new Chart(canvas.getContext("2d"), {
        type: chartType,
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true } },
            scales: { y: { beginAtZero: true } }
        }
    });
}

function formatWon(value) {
    return `${formatNumber(value)}원`;
}

function formatNumber(value) {
    const number = Number(value || 0);
    return number.toLocaleString("ko-KR");
}

function formatDateWithWeekday(date, weekday) {
    if (!date) return "데이터 없음";
    return weekday ? `${date} (${weekday})` : date;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

/* ============================================================
   기간비교 탭 3단계: 하위 탭 전환 + 단위 선택 기본 로직
   - 기존 분석 탭 로직은 건드리지 않음
   - 기간비교 관련 함수/변수는 period_ 접두사 사용
============================================================ */

let period_initialized = false;
let period_currentUnit = "day";

document.addEventListener("DOMContentLoaded", function () {
    period_initSubTabs();
});

function period_initSubTabs() {
    const tabs = document.querySelectorAll(".analytics-sub-tabs .sub-tab");
    const tabAnalysis = document.getElementById("tab-analysis");
    const tabPeriod = document.getElementById("tab-period");

    if (!tabs.length || !tabAnalysis || !tabPeriod) {
        return;
    }

    tabs.forEach((tab) => {
        tab.addEventListener("click", function () {
            const target = tab.dataset.tab;

            tabs.forEach((item) => item.classList.remove("active"));
            tab.classList.add("active");

            if (target === "analysis") {
                tabAnalysis.style.display = "block";
                tabPeriod.style.display = "none";
                return;
            }

            if (target === "period") {
                tabAnalysis.style.display = "none";
                tabPeriod.style.display = "block";

                if (!period_initialized) {
                    period_initPeriodTab();
                    period_initialized = true;
                }
            }
        });
    });

    tabAnalysis.style.display = "block";
    tabPeriod.style.display = "none";
}

function period_initPeriodTab() {
    period_currentUnit = "day";

    period_setDefaultReferenceValues();
    period_bindUnitButtons();
    period_bindGenerateButton();
    period_showReferenceInput("day");

    const container = document.getElementById("period-cards-container");
    if (container && container.children.length === 0) {
        container.innerHTML = `
            <div class="period-card-loading">
                기간비교 탭이 준비되었습니다.<br>
                다음 단계에서 카드 생성 기능이 연결됩니다.
            </div>
        `;
    }
}

function period_setDefaultReferenceValues() {
    const today = new Date();
    const todayText = period_formatDate(today);
    const monthText = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
    const year = today.getFullYear();
    const month = today.getMonth() + 1;

    const refDay = document.getElementById("ref-day");
    const refMonth = document.getElementById("ref-month");
    const refQuarterYear = document.getElementById("ref-quarter-year");
    const refQuarterQ = document.getElementById("ref-quarter-q");
    const refHalfYear = document.getElementById("ref-half-year");
    const refHalfH = document.getElementById("ref-half-h");
    const refYear = document.getElementById("ref-year");

    if (refDay) refDay.value = todayText;
    if (refMonth) refMonth.value = monthText;

    if (refQuarterYear) refQuarterYear.value = year;
    if (refQuarterQ) refQuarterQ.value = String(Math.floor((month - 1) / 3) + 1);

    if (refHalfYear) refHalfYear.value = year;
    if (refHalfH) refHalfH.value = month <= 6 ? "1" : "2";

    if (refYear) refYear.value = year;
}

function period_bindUnitButtons() {
    const unitButtons = document.querySelectorAll("#tab-period .unit-btn");

    unitButtons.forEach((button) => {
        button.addEventListener("click", function () {
            const nextUnit = button.dataset.unit;

            if (!nextUnit || nextUnit === period_currentUnit) {
                return;
            }

            const confirmed = confirm("기간 카드가 초기화됩니다. 계속할까요?");
            if (!confirmed) {
                return;
            }

            period_currentUnit = nextUnit;

            unitButtons.forEach((item) => item.classList.remove("active"));
            button.classList.add("active");

            period_showReferenceInput(nextUnit);

            const container = document.getElementById("period-cards-container");
            if (container) {
                container.innerHTML = `
                    <div class="period-card-loading">
                        ${period_getUnitName(nextUnit)} 단위가 선택되었습니다.<br>
                        다음 단계에서 카드 생성 기능이 연결됩니다.
                    </div>
                `;
            }
        });
    });
}

function period_bindGenerateButton() {
    const generateButton = document.getElementById("period-generate-btn");

    if (!generateButton) {
        return;
    }

    generateButton.addEventListener("click", function () {
        const range = period_getInitialRange(period_currentUnit);
        const container = document.getElementById("period-cards-container");

        if (container) {
            container.innerHTML = `
                <div class="period-card-loading">
                    ${period_getUnitName(period_currentUnit)} 기준 기간:<br>
                    ${range.start} ~ ${range.end}<br>
                    다음 단계에서 API 카드가 표시됩니다.
                </div>
            `;
        }
    });
}

function period_showReferenceInput(unit) {
    const wrapIds = [
        "ref-day-wrap",
        "ref-month-wrap",
        "ref-quarter-wrap",
        "ref-half-wrap",
        "ref-year-wrap"
    ];

    wrapIds.forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.style.display = "none";
    });

    const map = {
        day: "ref-day-wrap",
        week: "ref-day-wrap",
        month: "ref-month-wrap",
        quarter: "ref-quarter-wrap",
        half: "ref-half-wrap",
        year: "ref-year-wrap"
    };

    const target = document.getElementById(map[unit]);
    if (target) {
        target.style.display = "block";
    }
}

function period_getInitialRange(unit) {
    if (unit === "day") {
        const value = document.getElementById("ref-day")?.value || period_formatDate(new Date());
        return { start: value, end: value };
    }

    if (unit === "week") {
        const value = document.getElementById("ref-day")?.value || period_formatDate(new Date());
        const d = period_parseDate(value);
        const monday = period_getMonday(d);
        const sunday = period_addDays(monday, 6);
        return {
            start: period_formatDate(monday),
            end: period_formatDate(sunday)
        };
    }

    if (unit === "month") {
        const value = document.getElementById("ref-month")?.value;
        const today = new Date();
        const [year, month] = value
            ? value.split("-").map(Number)
            : [today.getFullYear(), today.getMonth() + 1];

        const start = new Date(year, month - 1, 1);
        const end = new Date(year, month, 0);

        return {
            start: period_formatDate(start),
            end: period_formatDate(end)
        };
    }

    if (unit === "quarter") {
        const year = Number(document.getElementById("ref-quarter-year")?.value || new Date().getFullYear());
        const q = Number(document.getElementById("ref-quarter-q")?.value || 1);
        const startMonth = (q - 1) * 3;
        const start = new Date(year, startMonth, 1);
        const end = new Date(year, startMonth + 3, 0);

        return {
            start: period_formatDate(start),
            end: period_formatDate(end)
        };
    }

    if (unit === "half") {
        const year = Number(document.getElementById("ref-half-year")?.value || new Date().getFullYear());
        const h = Number(document.getElementById("ref-half-h")?.value || 1);
        const start = h === 1 ? new Date(year, 0, 1) : new Date(year, 6, 1);
        const end = h === 1 ? new Date(year, 5, 30) : new Date(year, 11, 31);

        return {
            start: period_formatDate(start),
            end: period_formatDate(end)
        };
    }

    if (unit === "year") {
        const year = Number(document.getElementById("ref-year")?.value || new Date().getFullYear());

        return {
            start: `${year}-01-01`,
            end: `${year}-12-31`
        };
    }

    const todayText = period_formatDate(new Date());
    return { start: todayText, end: todayText };
}

function period_getMonday(dateObj) {
    const d = new Date(dateObj);
    const day = d.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    d.setDate(d.getDate() + diff);
    return d;
}

function period_addDays(dateObj, days) {
    const d = new Date(dateObj);
    d.setDate(d.getDate() + days);
    return d;
}

function period_parseDate(value) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
}

function period_formatDate(dateObj) {
    const year = dateObj.getFullYear();
    const month = String(dateObj.getMonth() + 1).padStart(2, "0");
    const day = String(dateObj.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function period_getUnitName(unit) {
    const names = {
        day: "일",
        week: "주",
        month: "월",
        quarter: "분기",
        half: "반기",
        year: "연간"
    };
    return names[unit] || unit;
}

/* ============================================================
   기간비교 탭 4단계: 실제 API 호출 + 첫 카드 생성
   - /api/analytics/period-summary 호출
   - 조회 버튼 클릭 시 카드 1개 생성
   - 기간비교 탭 최초 진입 시 오늘 기준 카드 1개 자동 생성
============================================================ */

let period_cards = [];

// 3단계에서 만든 함수를 덮어써서 첫 카드 자동 생성까지 연결
function period_initPeriodTab() {
    period_currentUnit = "day";
    period_cards = [];

    period_setDefaultReferenceValues();
    period_bindUnitButtons();
    period_bindGenerateButton();
    period_showReferenceInput("day");

    const range = period_getInitialRange("day");
    period_resetAndCreateFirstCard(range.start, range.end, "day");
}

// 3단계에서 만든 함수도 덮어써서 조회 버튼이 실제 카드를 생성하도록 변경
function period_bindGenerateButton() {
    const generateButton = document.getElementById("period-generate-btn");

    if (!generateButton) {
        return;
    }

    if (generateButton.dataset.periodBound === "1") {
        return;
    }

    generateButton.dataset.periodBound = "1";

    generateButton.addEventListener("click", function () {
        const range = period_getInitialRange(period_currentUnit);
        period_resetAndCreateFirstCard(range.start, range.end, period_currentUnit);
    });
}

// 3단계에서 만든 함수도 덮어써서 단위 변경 시 첫 카드 자동 생성
function period_bindUnitButtons() {
    const unitButtons = document.querySelectorAll("#tab-period .unit-btn");

    unitButtons.forEach((button) => {
        if (button.dataset.periodBound === "1") {
            return;
        }

        button.dataset.periodBound = "1";

        button.addEventListener("click", function () {
            const nextUnit = button.dataset.unit;

            if (!nextUnit || nextUnit === period_currentUnit) {
                return;
            }

            const confirmed = confirm("기간 카드가 초기화됩니다. 계속할까요?");
            if (!confirmed) {
                return;
            }

            period_currentUnit = nextUnit;
            period_cards = [];

            unitButtons.forEach((item) => item.classList.remove("active"));
            button.classList.add("active");

            period_showReferenceInput(nextUnit);

            const range = period_getInitialRange(nextUnit);
            period_resetAndCreateFirstCard(range.start, range.end, nextUnit);
        });
    });
}

function period_resetAndCreateFirstCard(start, end, unit) {
    const container = document.getElementById("period-cards-container");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    period_cards = [];

    period_createCard(start, end, unit);
    period_updateAddButtonState();
}

async function period_createCard(start, end, unit) {
    const container = document.getElementById("period-cards-container");
    if (!container) {
        return;
    }

    const card = document.createElement("div");
    card.className = "period-card";
    card.dataset.start = start;
    card.dataset.end = end;
    card.dataset.unit = unit;

    card.innerHTML = `
        <div class="period-card-loading">
            데이터를 불러오는 중...
        </div>
    `;

    container.appendChild(card);

    try {
        const url = `/api/analytics/period-summary?unit=${encodeURIComponent(unit)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok || data.ok === false) {
            card.innerHTML = `
                <div class="period-card-header">
                    <span class="period-card-label">오류</span>
                    <button type="button" class="period-card-delete">×</button>
                </div>
                <div class="period-card-range">${escapeHtml(start)} ~ ${escapeHtml(end)}</div>
                <div class="period-card-loading">${escapeHtml(data.error || "데이터 조회 실패")}</div>
            `;
            period_bindDeleteButton(card);
            period_updateDeleteButtonState();
            return;
        }

        card.dataset.start = data.start;
        card.dataset.end = data.end;
        card.dataset.unit = data.unit;

        period_renderCard(card, data);

        period_cards.push({
            start: data.start,
            end: data.end,
            unit: data.unit
        });

        period_updateDeleteButtonState();
        period_updateAddButtonState();

    } catch (error) {
        console.error(error);
        card.innerHTML = `
            <div class="period-card-header">
                <span class="period-card-label">오류</span>
                <button type="button" class="period-card-delete">×</button>
            </div>
            <div class="period-card-range">${escapeHtml(start)} ~ ${escapeHtml(end)}</div>
            <div class="period-card-loading">데이터를 불러오는 중 오류가 발생했습니다.</div>
        `;
        period_bindDeleteButton(card);
        period_updateDeleteButtonState();
    }
}

function period_renderCard(card, data) {
    const closingClass = data.closing >= 0 ? "closing-positive" : "closing-negative";
    const showWorkday = data.unit !== "day";

    const currentBadge = data.is_current
        ? `<span class="badge-current">● 진행 중</span>`
        : "";

    const noDataBadge = !data.has_data
        ? `<span class="badge-no-data">● 데이터 없음</span>`
        : "";

    card.innerHTML = `
        <div class="period-card-header">
            <span class="period-card-label">${escapeHtml(data.label)}</span>
            ${currentBadge}
            ${noDataBadge}
            <button type="button" class="period-card-delete">×</button>
        </div>

        <div class="period-card-range" data-action="open-modal">
            ${escapeHtml(data.start)} ~ ${escapeHtml(data.end)}
        </div>

        <div class="period-card-body">
            ${period_summaryRow("총내원", `${period_formatNumber(data.total_visit)}명`)}
            ${period_summaryRow("신환매출", period_formatWon(data.new_customer_sales))}
            ${period_summaryRow("구환매출", period_formatWon(data.returning_customer_sales))}
            ${period_summaryRow("총매출", period_formatWon(data.total_sales), true)}
            ${period_summaryRow("총지출", period_formatWon(data.total_expense))}
            ${period_summaryRow("결산", period_formatWon(data.closing), false, closingClass)}
            ${showWorkday ? period_summaryRow("근무일수", `${period_formatNumber(data.workday_count)}일`) : ""}
        </div>
    `;

    period_bindDeleteButton(card);
}

function period_summaryRow(label, value, highlight = false, extraClass = "") {
    return `
        <div class="summary-row">
            <span class="summary-label">${escapeHtml(label)}</span>
            <span class="summary-value ${highlight ? "highlight" : ""} ${extraClass}">${escapeHtml(value)}</span>
        </div>
    `;
}

function period_bindDeleteButton(card) {
    const deleteButton = card.querySelector(".period-card-delete");

    if (!deleteButton) {
        return;
    }

    deleteButton.addEventListener("click", function () {
        const container = document.getElementById("period-cards-container");

        if (!container) {
            return;
        }

        const cards = container.querySelectorAll(".period-card");

        if (cards.length <= 1) {
            return;
        }

        card.remove();

        period_cards = Array.from(container.querySelectorAll(".period-card")).map((item) => ({
            start: item.dataset.start,
            end: item.dataset.end,
            unit: item.dataset.unit
        }));

        period_updateDeleteButtonState();
        period_updateAddButtonState();
    });
}

function period_updateDeleteButtonState() {
    const cards = document.querySelectorAll("#period-cards-container .period-card");
    const isSingle = cards.length <= 1;

    cards.forEach((card) => {
        const btn = card.querySelector(".period-card-delete");
        if (btn) {
            btn.disabled = isSingle;
            btn.title = isSingle ? "최소 1개 카드는 유지해야 합니다." : "카드 삭제";
        }
    });
}

function period_updateAddButtonState() {
    const addButton = document.getElementById("add-period-card-btn");
    const cards = document.querySelectorAll("#period-cards-container .period-card");

    if (!addButton) {
        return;
    }

    if (cards.length >= 12) {
        addButton.disabled = true;
        addButton.title = "최대 12개까지 추가 가능";
    } else {
        addButton.disabled = false;
        addButton.title = "기간 추가";
    }
}

function period_formatWon(value) {
    return `${period_formatNumber(value)}원`;
}

function period_formatNumber(value) {
    const number = Number(value || 0);
    return number.toLocaleString("ko-KR");
}

// 기존 analytics.js에 escapeHtml이 없을 수도 있어서 안전하게 정의
if (typeof escapeHtml !== "function") {
    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }
}

/* ============================================================
   기간비교 탭 5단계: + 버튼으로 다음 기간 카드 추가
   - 마지막 카드 기준 다음 기간 자동 계산
   - 최대 12개 제한
   - 기존 분석 탭 로직은 건드리지 않음
============================================================ */

document.addEventListener("DOMContentLoaded", function () {
    period_bindAddButtonWhenReady();
});

function period_bindAddButtonWhenReady() {
    const addButton = document.getElementById("add-period-card-btn");

    if (!addButton) {
        return;
    }

    if (addButton.dataset.periodBound === "1") {
        return;
    }

    addButton.dataset.periodBound = "1";

    addButton.addEventListener("click", function () {
        period_addNextCard();
    });
}

function period_addNextCard() {
    const container = document.getElementById("period-cards-container");
    const addButton = document.getElementById("add-period-card-btn");

    if (!container || !addButton) {
        return;
    }

    const cards = container.querySelectorAll(".period-card");

    if (cards.length >= 12) {
        addButton.disabled = true;
        addButton.title = "최대 12개까지 추가 가능";
        return;
    }

    if (cards.length === 0) {
        const range = period_getInitialRange(period_currentUnit || "day");
        period_createCard(range.start, range.end, period_currentUnit || "day");
        return;
    }

    const lastCard = cards[cards.length - 1];
    const currentStart = lastCard.dataset.start;
    const currentEnd = lastCard.dataset.end;
    const unit = lastCard.dataset.unit || period_currentUnit || "day";

    const nextRange = period_getNextRange(currentStart, currentEnd, unit);

    period_createCard(nextRange.start, nextRange.end, unit);
    period_updateAddButtonState();
}

function period_getNextRange(currentStart, currentEnd, unit) {
    const startDate = period_parseDate(currentStart);
    const endDate = period_parseDate(currentEnd);

    if (unit === "day") {
        const next = period_addDays(endDate, 1);
        return {
            start: period_formatDate(next),
            end: period_formatDate(next)
        };
    }

    if (unit === "week") {
        const nextStart = period_addDays(startDate, 7);
        const nextEnd = period_addDays(endDate, 7);
        return {
            start: period_formatDate(nextStart),
            end: period_formatDate(nextEnd)
        };
    }

    if (unit === "month") {
        const nextStart = new Date(startDate.getFullYear(), startDate.getMonth() + 1, 1);
        const nextEnd = new Date(nextStart.getFullYear(), nextStart.getMonth() + 1, 0);
        return {
            start: period_formatDate(nextStart),
            end: period_formatDate(nextEnd)
        };
    }

    if (unit === "quarter") {
        const nextStart = new Date(startDate.getFullYear(), startDate.getMonth() + 3, 1);
        const quarter = Math.floor(nextStart.getMonth() / 3) + 1;
        const quarterStartMonth = (quarter - 1) * 3;
        const normalizedStart = new Date(nextStart.getFullYear(), quarterStartMonth, 1);
        const nextEnd = new Date(normalizedStart.getFullYear(), normalizedStart.getMonth() + 3, 0);

        return {
            start: period_formatDate(normalizedStart),
            end: period_formatDate(nextEnd)
        };
    }

    if (unit === "half") {
        const nextStart = new Date(startDate.getFullYear(), startDate.getMonth() + 6, 1);
        const halfStartMonth = nextStart.getMonth() < 6 ? 0 : 6;
        const normalizedStart = new Date(nextStart.getFullYear(), halfStartMonth, 1);
        const nextEnd = halfStartMonth === 0
            ? new Date(normalizedStart.getFullYear(), 5, 30)
            : new Date(normalizedStart.getFullYear(), 11, 31);

        return {
            start: period_formatDate(normalizedStart),
            end: period_formatDate(nextEnd)
        };
    }

    if (unit === "year") {
        const year = startDate.getFullYear() + 1;
        return {
            start: `${year}-01-01`,
            end: `${year}-12-31`
        };
    }

    const fallback = period_addDays(endDate, 1);
    return {
        start: period_formatDate(fallback),
        end: period_formatDate(fallback)
    };
}

// 기존 period_resetAndCreateFirstCard 함수를 덮어써서 + 버튼 상태까지 안정적으로 갱신
function period_resetAndCreateFirstCard(start, end, unit) {
    const container = document.getElementById("period-cards-container");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    period_cards = [];

    period_createCard(start, end, unit);
    period_updateAddButtonState();
}

// 기존 period_updateAddButtonState 함수가 없거나 약한 경우를 대비해 재정의
function period_updateAddButtonState() {
    const addButton = document.getElementById("add-period-card-btn");
    const cards = document.querySelectorAll("#period-cards-container .period-card");

    if (!addButton) {
        return;
    }

    if (cards.length >= 12) {
        addButton.disabled = true;
        addButton.title = "최대 12개까지 추가 가능";
    } else {
        addButton.disabled = false;
        addButton.title = "기간 추가";
    }
}

/* ============================================================
   기간비교 탭 6단계: 카드 삭제 안정화 + 최소 1개 유지
   - 카드 삭제 후 남은 카드 상태 재정리
   - 카드가 1개면 × 버튼 비활성화
   - 삭제 후 + 버튼 상태 갱신
   - 기존 분석 탭 로직은 건드리지 않음
============================================================ */

document.addEventListener("DOMContentLoaded", function () {
    period_refreshDeleteStateWhenReady();
});

function period_refreshDeleteStateWhenReady() {
    setTimeout(function () {
        period_updateDeleteButtonState();
        period_updateAddButtonState();
    }, 300);
}

// 기존 period_bindDeleteButton 함수를 더 안정적인 버전으로 재정의
function period_bindDeleteButton(card) {
    const deleteButton = card.querySelector(".period-card-delete");

    if (!deleteButton) {
        return;
    }

    if (deleteButton.dataset.periodBound === "1") {
        return;
    }

    deleteButton.dataset.periodBound = "1";

    deleteButton.addEventListener("click", function () {
        const container = document.getElementById("period-cards-container");

        if (!container) {
            return;
        }

        const cards = Array.from(container.querySelectorAll(".period-card"));

        if (cards.length <= 1) {
            deleteButton.disabled = true;
            deleteButton.title = "최소 1개 카드는 유지해야 합니다.";
            return;
        }

        const confirmed = confirm("이 기간 카드를 삭제할까요?");
        if (!confirmed) {
            return;
        }

        card.remove();

        period_rebuildCardsState();
        period_updateDeleteButtonState();
        period_updateAddButtonState();
    });
}

function period_rebuildCardsState() {
    const container = document.getElementById("period-cards-container");

    if (!container) {
        period_cards = [];
        return;
    }

    period_cards = Array.from(container.querySelectorAll(".period-card")).map((item) => ({
        start: item.dataset.start,
        end: item.dataset.end,
        unit: item.dataset.unit || period_currentUnit || "day"
    }));
}

// 기존 period_updateDeleteButtonState 함수를 더 안정적인 버전으로 재정의
function period_updateDeleteButtonState() {
    const cards = document.querySelectorAll("#period-cards-container .period-card");
    const isSingle = cards.length <= 1;

    cards.forEach((card) => {
        const btn = card.querySelector(".period-card-delete");

        if (!btn) {
            return;
        }

        btn.disabled = isSingle;
        btn.title = isSingle ? "최소 1개 카드는 유지해야 합니다." : "카드 삭제";
    });
}

// 기존 period_renderCard 함수를 재정의해서 카드 렌더링 후 삭제 상태를 확실히 갱신
function period_renderCard(card, data) {
    const closingClass = data.closing >= 0 ? "closing-positive" : "closing-negative";
    const showWorkday = data.unit !== "day";

    const currentBadge = data.is_current
        ? `<span class="badge-current">● 진행 중</span>`
        : "";

    const noDataBadge = !data.has_data
        ? `<span class="badge-no-data">● 데이터 없음</span>`
        : "";

    card.innerHTML = `
        <div class="period-card-header">
            <span class="period-card-label">${escapeHtml(data.label)}</span>
            ${currentBadge}
            ${noDataBadge}
            <button type="button" class="period-card-delete">×</button>
        </div>

        <div class="period-card-range" data-action="open-modal">
            ${escapeHtml(data.start)} ~ ${escapeHtml(data.end)}
        </div>

        <div class="period-card-body">
            ${period_summaryRow("총내원", `${period_formatNumber(data.total_visit)}명`)}
            ${period_summaryRow("신환매출", period_formatWon(data.new_customer_sales))}
            ${period_summaryRow("구환매출", period_formatWon(data.returning_customer_sales))}
            ${period_summaryRow("총매출", period_formatWon(data.total_sales), true)}
            ${period_summaryRow("총지출", period_formatWon(data.total_expense))}
            ${period_summaryRow("결산", period_formatWon(data.closing), false, closingClass)}
            ${showWorkday ? period_summaryRow("근무일수", `${period_formatNumber(data.workday_count)}일`) : ""}
        </div>
    `;

    period_bindDeleteButton(card);
    period_updateDeleteButtonState();
    period_updateAddButtonState();
}

/* ============================================================
   기간비교 6.1단계: 삭제/추가 버튼 상태 강제 보정
   - 카드 1개면 × 버튼 비활성화
   - 카드 12개면 + 버튼 비활성화
   - 카드가 추가/삭제/조회될 때마다 상태 재계산
   - 기존 데이터 DB는 건드리지 않음
============================================================ */

document.addEventListener("DOMContentLoaded", function () {
    period_forceBindButtonStateWatcher();
});

function period_forceBindButtonStateWatcher() {
    const container = document.getElementById("period-cards-container");
    const addButton = document.getElementById("add-period-card-btn");

    if (!container && !addButton) {
        return;
    }

    // + 버튼 바인딩 보정
    if (addButton && addButton.dataset.periodForceBound !== "1") {
        addButton.dataset.periodForceBound = "1";
        addButton.addEventListener("click", function (event) {
            const count = period_getCardCount();

            if (count >= 12) {
                event.preventDefault();
                event.stopPropagation();
                period_forceUpdateButtonStates();
                return false;
            }
        }, true);
    }

    // 카드 영역 변화 감지: 카드가 추가/삭제/재렌더링될 때마다 버튼 상태 갱신
    if (container && container.dataset.periodObserverBound !== "1") {
        container.dataset.periodObserverBound = "1";

        const observer = new MutationObserver(function () {
            period_forceUpdateButtonStates();
            period_forceBindDeleteButtons();
        });

        observer.observe(container, {
            childList: true,
            subtree: true
        });
    }

    // 최초 1회 + 약간 늦게 1회 더 보정
    period_forceUpdateButtonStates();
    period_forceBindDeleteButtons();

    setTimeout(function () {
        period_forceUpdateButtonStates();
        period_forceBindDeleteButtons();
    }, 500);
}

function period_getCardCount() {
    return document.querySelectorAll("#period-cards-container .period-card").length;
}

function period_forceUpdateButtonStates() {
    const cards = Array.from(document.querySelectorAll("#period-cards-container .period-card"));
    const addButton = document.getElementById("add-period-card-btn");
    const count = cards.length;

    // × 버튼 상태
    cards.forEach((card) => {
        const deleteButton = card.querySelector(".period-card-delete");
        if (!deleteButton) return;

        if (count <= 1) {
            deleteButton.disabled = true;
            deleteButton.setAttribute("disabled", "disabled");
            deleteButton.title = "최소 1개 카드는 유지해야 합니다.";
            deleteButton.style.opacity = "0.25";
            deleteButton.style.cursor = "default";
        } else {
            deleteButton.disabled = false;
            deleteButton.removeAttribute("disabled");
            deleteButton.title = "카드 삭제";
            deleteButton.style.opacity = "";
            deleteButton.style.cursor = "";
        }
    });

    // + 버튼 상태
    if (addButton) {
        if (count >= 12) {
            addButton.disabled = true;
            addButton.setAttribute("disabled", "disabled");
            addButton.title = "최대 12개까지 추가 가능";
            addButton.style.opacity = "0.3";
            addButton.style.cursor = "default";
        } else {
            addButton.disabled = false;
            addButton.removeAttribute("disabled");
            addButton.title = "기간 추가";
            addButton.style.opacity = "";
            addButton.style.cursor = "";
        }
    }
}

function period_forceBindDeleteButtons() {
    const cards = Array.from(document.querySelectorAll("#period-cards-container .period-card"));

    cards.forEach((card) => {
        const deleteButton = card.querySelector(".period-card-delete");
        if (!deleteButton) return;

        if (deleteButton.dataset.periodForceDeleteBound === "1") {
            return;
        }

        deleteButton.dataset.periodForceDeleteBound = "1";

        deleteButton.addEventListener("click", function (event) {
            const currentCount = period_getCardCount();

            if (currentCount <= 1) {
                event.preventDefault();
                event.stopPropagation();
                period_forceUpdateButtonStates();
                return false;
            }

            // 기존 삭제 로직이 이미 있으면 그것을 우선 사용하되,
            // 삭제 이후 상태가 다시 맞도록 늦게 한 번 더 보정
            setTimeout(function () {
                period_forceUpdateButtonStates();
                period_forceBindDeleteButtons();
            }, 100);
        }, true);
    });
}

// 기존 상태 갱신 함수도 강제 보정 버전으로 덮어쓰기
function period_updateDeleteButtonState() {
    period_forceUpdateButtonStates();
}

function period_updateAddButtonState() {
    period_forceUpdateButtonStates();
}

/* ============================================================
   기간비교 탭 7단계: 기간 수정 모달
   - 카드 날짜 범위 클릭 시 모달 열기
   - 시작일/종료일 수정
   - start > end 저장 차단
   - 확인 시 해당 카드만 API 재조회 후 갱신
   - 기존 분석 탭 로직은 건드리지 않음
============================================================ */

let period_editTargetCard = null;

document.addEventListener("DOMContentLoaded", function () {
    period_bindModalBaseEventsWhenReady();
    period_bindCardRangeClickObserver();
});

function period_bindModalBaseEventsWhenReady() {
    const modal = document.getElementById("period-edit-modal");
    const confirmButton = document.getElementById("modal-edit-confirm");
    const cancelButton = document.getElementById("modal-edit-cancel");

    if (!modal || !confirmButton || !cancelButton) {
        return;
    }

    if (modal.dataset.periodModalBound === "1") {
        return;
    }

    modal.dataset.periodModalBound = "1";

    confirmButton.addEventListener("click", function () {
        period_confirmEditModal();
    });

    cancelButton.addEventListener("click", function () {
        period_closeEditModal();
    });

    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            period_closeEditModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modal.style.display !== "none") {
            period_closeEditModal();
        }
    });
}

function period_bindCardRangeClickObserver() {
    const container = document.getElementById("period-cards-container");

    if (!container) {
        return;
    }

    if (container.dataset.periodRangeObserverBound === "1") {
        return;
    }

    container.dataset.periodRangeObserverBound = "1";

    container.addEventListener("click", function (event) {
        const rangeEl = event.target.closest(".period-card-range");

        if (!rangeEl) {
            return;
        }

        const card = rangeEl.closest(".period-card");

        if (!card) {
            return;
        }

        period_openEditModal(card);
    });
}

function period_openEditModal(card) {
    const modal = document.getElementById("period-edit-modal");
    const startInput = document.getElementById("modal-edit-start");
    const endInput = document.getElementById("modal-edit-end");
    const errorEl = document.getElementById("modal-edit-error");

    if (!modal || !startInput || !endInput) {
        alert("기간 수정 모달을 찾을 수 없습니다.");
        return;
    }

    period_editTargetCard = card;

    startInput.value = card.dataset.start || "";
    endInput.value = card.dataset.end || "";

    if (errorEl) {
        errorEl.style.display = "none";
    }

    modal.style.display = "flex";
    startInput.focus();
}

function period_closeEditModal() {
    const modal = document.getElementById("period-edit-modal");
    const errorEl = document.getElementById("modal-edit-error");

    if (modal) {
        modal.style.display = "none";
    }

    if (errorEl) {
        errorEl.style.display = "none";
    }

    period_editTargetCard = null;
}

async function period_confirmEditModal() {
    const startInput = document.getElementById("modal-edit-start");
    const endInput = document.getElementById("modal-edit-end");
    const errorEl = document.getElementById("modal-edit-error");

    if (!period_editTargetCard || !startInput || !endInput) {
        period_closeEditModal();
        return;
    }

    const start = startInput.value;
    const end = endInput.value;

    if (!start || !end || start > end) {
        if (errorEl) {
            errorEl.textContent = "시작일이 종료일보다 늦을 수 없습니다";
            errorEl.style.display = "block";
        }
        return;
    }

    const card = period_editTargetCard;
    const unit = card.dataset.unit || period_currentUnit || "day";

    period_closeEditModal();

    await period_reloadCard(card, start, end, unit);
    period_rebuildCardsState();
    period_forceUpdateButtonStates?.();
}

async function period_reloadCard(card, start, end, unit) {
    if (!card) {
        return;
    }

    card.dataset.start = start;
    card.dataset.end = end;
    card.dataset.unit = unit;

    card.innerHTML = `
        <div class="period-card-loading">
            수정한 기간 데이터를 불러오는 중...
        </div>
    `;

    try {
        const url = `/api/analytics/period-summary?unit=${encodeURIComponent(unit)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok || data.ok === false) {
            card.innerHTML = `
                <div class="period-card-header">
                    <span class="period-card-label">오류</span>
                    <button type="button" class="period-card-delete">×</button>
                </div>
                <div class="period-card-range">${escapeHtml(start)} ~ ${escapeHtml(end)}</div>
                <div class="period-card-loading">${escapeHtml(data.error || "데이터 조회 실패")}</div>
            `;

            period_bindDeleteButton(card);
            period_updateDeleteButtonState();
            period_updateAddButtonState();
            return;
        }

        card.dataset.start = data.start;
        card.dataset.end = data.end;
        card.dataset.unit = data.unit;

        period_renderCard(card, data);

        period_rebuildCardsState();
        period_updateDeleteButtonState();
        period_updateAddButtonState();

    } catch (error) {
        console.error(error);

        card.innerHTML = `
            <div class="period-card-header">
                <span class="period-card-label">오류</span>
                <button type="button" class="period-card-delete">×</button>
            </div>
            <div class="period-card-range">${escapeHtml(start)} ~ ${escapeHtml(end)}</div>
            <div class="period-card-loading">데이터를 불러오는 중 오류가 발생했습니다.</div>
        `;

        period_bindDeleteButton(card);
        period_updateDeleteButtonState();
        period_updateAddButtonState();
    }
}

/* ============================================================
   기간비교 7.2단계: 명확한 기간 수정 모달
   - 제목/닫기 X/취소/확인 버튼을 확실히 표시
   - ESC 대신 '취소' 버튼으로 닫을 수 있게 명확화
   - 바깥 클릭 닫기는 유지
============================================================ */

document.addEventListener("DOMContentLoaded", function () {
    period_upgradeEditModalUI();
    period_rebindClearModalEvents();
});

function period_upgradeEditModalUI() {
    const modal = document.getElementById("period-edit-modal");
    if (!modal) return;

    const box = modal.querySelector(".modal-box");
    if (!box) return;

    if (box.dataset.periodClearModalUpgraded === "1") return;
    box.dataset.periodClearModalUpgraded = "1";

    box.innerHTML = `
        <div class="modal-title-row">
            <h3>기간 수정</h3>
            <button type="button" id="modal-edit-close-x" aria-label="닫기">×</button>
        </div>

        <p class="modal-help-text">
            이 카드에 표시할 시작일과 종료일을 선택한 뒤 확인을 누르세요.
        </p>

        <div>
            <label>시작일
                <input type="date" id="modal-edit-start">
            </label>
        </div>

        <div>
            <label>종료일
                <input type="date" id="modal-edit-end">
            </label>
        </div>

        <p id="modal-edit-error" style="color:#C0392B;display:none">
            시작일이 종료일보다 늦을 수 없습니다
        </p>

        <div class="modal-actions">
            <button type="button" id="modal-edit-cancel">취소</button>
            <button type="button" id="modal-edit-confirm">확인</button>
        </div>
    `;
}

function period_rebindClearModalEvents() {
    const modal = document.getElementById("period-edit-modal");
    const container = document.getElementById("period-cards-container");
    if (!modal || !container) return;

    if (container.dataset.periodClearModalClickBound !== "1") {
        container.dataset.periodClearModalClickBound = "1";

        container.addEventListener("click", function (event) {
            const rangeEl = event.target.closest(".period-card-range");
            if (!rangeEl) return;

            const card = rangeEl.closest(".period-card");
            if (!card) return;

            event.preventDefault();
            event.stopPropagation();
            period_openClearEditModal(card);
        }, true);
    }

    if (modal.dataset.periodClearModalBackdropBound !== "1") {
        modal.dataset.periodClearModalBackdropBound = "1";

        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                period_closeClearEditModal();
            }
        });
    }

    document.addEventListener("click", function (event) {
        const target = event.target;

        if (target && target.id === "modal-edit-cancel") {
            event.preventDefault();
            event.stopPropagation();
            period_closeClearEditModal();
        }

        if (target && target.id === "modal-edit-close-x") {
            event.preventDefault();
            event.stopPropagation();
            period_closeClearEditModal();
        }

        if (target && target.id === "modal-edit-confirm") {
            event.preventDefault();
            event.stopPropagation();
            period_confirmClearEditModal();
        }
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modal.classList.contains("period-modal-visible")) {
            period_closeClearEditModal();
        }
    });
}

function period_openClearEditModal(card) {
    period_upgradeEditModalUI();

    const modal = document.getElementById("period-edit-modal");
    const startInput = document.getElementById("modal-edit-start");
    const endInput = document.getElementById("modal-edit-end");
    const errorEl = document.getElementById("modal-edit-error");

    if (!modal || !startInput || !endInput) {
        alert("기간 수정 창을 찾을 수 없습니다.");
        return;
    }

    window.period_editTargetCard = card;
    if (typeof period_editTargetCard !== "undefined") {
        period_editTargetCard = card;
    }

    startInput.value = card.dataset.start || "";
    endInput.value = card.dataset.end || "";

    if (errorEl) {
        errorEl.style.display = "none";
    }

    modal.classList.add("period-modal-visible");
    modal.style.display = "flex";
    startInput.focus();
}

function period_closeClearEditModal() {
    const modal = document.getElementById("period-edit-modal");
    const errorEl = document.getElementById("modal-edit-error");

    if (modal) {
        modal.classList.remove("period-modal-visible");
        modal.style.display = "none";
    }

    if (errorEl) {
        errorEl.style.display = "none";
    }

    window.period_editTargetCard = null;
    if (typeof period_editTargetCard !== "undefined") {
        period_editTargetCard = null;
    }
}

async function period_confirmClearEditModal() {
    const card = window.period_editTargetCard || (typeof period_editTargetCard !== "undefined" ? period_editTargetCard : null);
    const startInput = document.getElementById("modal-edit-start");
    const endInput = document.getElementById("modal-edit-end");
    const errorEl = document.getElementById("modal-edit-error");

    if (!card || !startInput || !endInput) {
        period_closeClearEditModal();
        return;
    }

    const start = startInput.value;
    const end = endInput.value;

    if (!start || !end || start > end) {
        if (errorEl) {
            errorEl.style.display = "block";
        }
        return;
    }

    const unit = card.dataset.unit || period_currentUnit || "day";
    period_closeClearEditModal();

    if (typeof period_reloadCard === "function") {
        await period_reloadCard(card, start, end, unit);
    } else {
        card.dataset.start = start;
        card.dataset.end = end;
        const rangeEl = card.querySelector(".period-card-range");
        if (rangeEl) {
            rangeEl.textContent = `${start} ~ ${end}`;
        }
    }

    if (typeof period_rebuildCardsState === "function") {
        period_rebuildCardsState();
    }
    if (typeof period_forceUpdateButtonStates === "function") {
        period_forceUpdateButtonStates();
    }
}

/* ============================================================
   기간비교 8.1단계: + 버튼을 조회 버튼 옆으로 이동
============================================================ */

document.addEventListener("DOMContentLoaded", function () {
    period_moveAddButtonNextToGenerate();
});

function period_moveAddButtonNextToGenerate() {
    const addButton = document.getElementById("add-period-card-btn");
    const generateButton = document.getElementById("period-generate-btn");

    if (!addButton || !generateButton) {
        return;
    }

    if (addButton.dataset.periodMovedToTop === "1") {
        return;
    }

    addButton.dataset.periodMovedToTop = "1";
    addButton.title = addButton.disabled ? "최대 12개까지 추가 가능" : "기간 추가";
    addButton.textContent = "+";

    generateButton.insertAdjacentElement("afterend", addButton);

    if (typeof period_forceUpdateButtonStates === "function") {
        period_forceUpdateButtonStates();
    } else if (typeof period_updateAddButtonState === "function") {
        period_updateAddButtonState();
    }
}

setTimeout(function () {
    period_moveAddButtonNextToGenerate();
}, 500);
