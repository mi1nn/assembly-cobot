"use strict";

const WORK_ORDER_POLL_INTERVAL_MS = 3000;
const LOGS_API_URL = "/api/v1/logs";
const DASHBOARD_API_URL =
    "/api/v1/dashboard";

const WORK_ORDERS_API_URL =
    "/api/v1/work-orders";

const ACTIVE_INSTALLATIONS_API_URL =
    "/api/v1/installations/active";

const WORK_EXECUTIONS_API_URL =
    "/api/v1/executions/work-executions";

let dashboardRobots = [];
let selectedHistoryWorkExecutionId = null;
let selectedHistoryOperationExecutionId = null;

document.addEventListener(
    "DOMContentLoaded",
    () => {
        initializeNavigation();
        initializeWorkOrderModal();
        initializeHistorySelectors();

        const refreshButton =
            document.getElementById(
                "refresh-button",
            );

        const workOrderForm =
            document.getElementById(
                "work-order-form",
            );

        const historyRefreshButton =
            document.getElementById(
                "history-refresh-button",
            );

        const dashboardWorkRefreshButton =
            document.getElementById(
                "dashboard-work-refresh-button",
            );

        refreshButton.addEventListener(
            "click",
            () => Promise.all([
                loadActiveInstallations(true),
                loadWorkOrders(true),
            ]),
        );

        historyRefreshButton.addEventListener(
            "click",
            () => loadSystemLogs(true),
        );

        dashboardWorkRefreshButton.addEventListener(
            "click",
            () => loadWorkOrders(true),
        );

        workOrderForm.addEventListener(
            "submit",
            handleWorkOrderSubmit,
        );

        loadInitialData();

        window.setInterval(
            refreshApplicationData,
            WORK_ORDER_POLL_INTERVAL_MS,
        );
    },
);

async function loadInitialData() {
    await loadDashboard();

    await Promise.all([
        loadActiveInstallations(),
        loadWorkOrders(),
        loadSystemLogs(),
        loadRecentLogs(),
        loadHistoryWorkExecutions(),
    ]);
}

async function refreshApplicationData() {
    await loadDashboard(false);

    await Promise.all([
        loadActiveInstallations(false),
        loadWorkOrders(false),
        loadSystemLogs(false),
        loadRecentLogs(false),
    ]);
}

function initializeNavigation() {
    const navigationButtons =
        document.querySelectorAll(
            ".nav-button[data-view]",
        );

    for (const button of navigationButtons) {
        button.addEventListener(
            "click",
            () => {
                showView(button.dataset.view);
            },
        );
    }
    const openHistoryButton =
        document.getElementById(
            "open-history-button",
        );

    openHistoryButton.addEventListener(
        "click",
        () => {
            showView("history-view");
        },
    );
}

function showView(viewId) {
    const targetView =
        document.getElementById(viewId);

    if (!targetView) {
        console.error(
            `View를 찾을 수 없습니다: ${viewId}`,
        );
        return;
    }

    const views =
        document.querySelectorAll(".app-view");

    for (const view of views) {
        const isActive = view === targetView;

        view.classList.toggle(
            "active",
            isActive,
        );

        view.hidden = !isActive;
    }

    const navigationButtons =
        document.querySelectorAll(".nav-button");

    for (const button of navigationButtons) {
        const isActive =
            button.dataset.view === viewId;

        button.classList.toggle(
            "active",
            isActive,
        );

        if (isActive) {
            button.setAttribute(
                "aria-current",
                "page",
            );
        } else {
            button.removeAttribute(
                "aria-current",
            );
        }
    }

    const pageTitle =
        document.getElementById("page-title");

    const pageDescription =
        document.getElementById(
            "page-description",
        );

    pageTitle.textContent =
        targetView.dataset.title
        ?? "Assembly Cobot";

    pageDescription.textContent =
        targetView.dataset.description
        ?? "";
}

function initializeHistorySelectors() {
    const workSelect =
        document.getElementById(
            "history-work-execution",
        );

    const operationSelect =
        document.getElementById(
            "history-operation-execution",
        );

    workSelect.addEventListener(
        "change",
        () => {
            const workExecutionId =
                Number(workSelect.value);

            selectedHistoryWorkExecutionId =
                workExecutionId || null;

            selectedHistoryOperationExecutionId =
                null;

            if (!workExecutionId) {
                resetHistoryOperationSelect();
                renderOperationSummary(null);
                loadSystemLogs();
                return;
            }

            loadHistoryOperationExecutions(
                workExecutionId,
            );

            loadSystemLogs();
        },
    );

    operationSelect.addEventListener(
        "change",
        () => {
            const selectedOption =
                operationSelect
                    .selectedOptions[0];

            selectedHistoryOperationExecutionId =
                Number(selectedOption?.value)
                || null;

            if (!selectedOption?.value) {
                renderOperationSummary(null);
                loadSystemLogs();
                return;
            }

            const operationData =
                JSON.parse(
                    selectedOption.dataset
                        .operation,
                );

            renderOperationSummary(
                operationData,
            );

            loadSystemLogs();
        },
    );
}

async function loadHistoryWorkExecutions() {
    const select =
        document.getElementById(
            "history-work-execution",
        );

    try {
        const response = await fetch(
            `${WORK_EXECUTIONS_API_URL}?limit=100`,
            {
                headers: {
                    "Accept": "application/json",
                },
            },
        );

        const responseData =
            await response.json();

        if (
            !response.ok
            || !responseData.success
        ) {
            throw new Error(
                responseData.error?.message
                ?? "Work Execution 조회에 실패했습니다.",
            );
        }

        select.replaceChildren();

        const placeholder =
            document.createElement("option");

        placeholder.value = "";
        placeholder.textContent =
            "Work Execution 선택";

        select.appendChild(placeholder);

        for (const execution of responseData.data) {
            const option =
                document.createElement("option");

            option.value = String(
                execution.work_execution_id,
            );

            option.textContent = [
                execution.execution_number,
                `Work ${execution.work_order_id}`,
                `Robot ${execution.robot_id}`,
                execution.status,
            ].join(" · ");

            select.appendChild(option);
        }
    } catch (error) {
        console.error(
            "Failed to load work executions:",
            error,
        );

        select.replaceChildren();

        const option =
            document.createElement("option");

        option.value = "";
        option.textContent =
            "Work Execution 조회 실패";

        select.appendChild(option);
    }
}


function initializeWorkOrderModal() {
    const openButtons =
        document.querySelectorAll(
            ".open-work-order-modal-button",
        );

    const closeButton =
        document.getElementById(
            "close-work-order-modal",
        );

    const cancelButton =
        document.getElementById(
            "cancel-work-order-modal",
        );

    const modal =
        document.getElementById(
            "work-order-modal",
        );

    for (const openButton of openButtons) {
        openButton.addEventListener(
            "click",
            openWorkOrderModal,
        );
    }

    closeButton.addEventListener(
        "click",
        closeWorkOrderModal,
    );

    cancelButton.addEventListener(
        "click",
        closeWorkOrderModal,
    );

    modal.addEventListener(
        "click",
        (event) => {
            if (event.target === modal) {
                closeWorkOrderModal();
            }
        },
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape"
                && !modal.hidden
            ) {
                closeWorkOrderModal();
            }
        },
    );
}

function openWorkOrderModal() {
    const modal =
        document.getElementById(
            "work-order-modal",
        );

    modal.hidden = false;

    document.body.classList.add(
        "modal-open",
    );

    document.getElementById(
        "order-number",
    ).focus();
}

function closeWorkOrderModal() {
    const modal =
        document.getElementById(
            "work-order-modal",
        );

    modal.hidden = true;

    document.body.classList.remove(
        "modal-open",
    );
}


async function loadDashboard(
    showLoading = true,
) {
    const robotList =
        document.getElementById(
            "robot-status-list",
        );

    if (showLoading) {
        robotList.textContent =
            "Robot 상태를 불러오는 중입니다.";
    }

    try {
        const response = await fetch(
            DASHBOARD_API_URL,
            {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            },
        );

        const responseData =
            await response.json();

        if (
            !response.ok
            || !responseData.success
        ) {
            throw new Error(
                responseData.error?.message
                ?? "Dashboard 조회에 실패했습니다.",
            );
        }

        dashboardRobots = Array.isArray(
            responseData.data?.robots,
        )
            ? responseData.data.robots
            : [];

        renderRobots(dashboardRobots);

        renderSuccessRate(
            responseData.data
                ?.work_execution_summary,
        );
    } catch (error) {
        console.error(
            "Failed to load dashboard:",
            error,
        );

        robotList.innerHTML =
            '<p class="error-message">'
            + 'Robot 상태를 불러오지 못했습니다.'
            + '</p>';
    }
}

function renderRobots(robots) {
    const robotList =
        document.getElementById(
            "robot-status-list",
        );

    robotList.replaceChildren();

    if (
        !Array.isArray(robots)
        || robots.length === 0
    ) {
        const message =
            document.createElement("p");

        message.className = "empty-message";
        message.textContent =
            "등록된 Robot이 없습니다.";

        robotList.appendChild(message);
        return;
    }

    for (const robot of robots) {
        const card =
            document.createElement("article");

        card.className = "robot-status-card";
        card.dataset.status =
            robot.status ?? "UNKNOWN";

        const identity =
            document.createElement("div");

        const name =
            document.createElement("strong");

        name.textContent =
            robot.name
            ?? `Robot ${robot.robot_id}`;

        const code =
            document.createElement("span");

        code.textContent =
            `${robot.robot_code ?? "-"} · ID ${robot.robot_id}`;

        identity.append(name, code);

        const status =
            document.createElement("span");

        status.className = "robot-status-badge";
        status.textContent =
            robot.status ?? "UNKNOWN";

        card.append(identity, status);

        if (robot.work_execution_id) {
            const execution =
                document.createElement("small");

            execution.textContent =
                `Work Execution ${robot.work_execution_id}`;

            card.appendChild(execution);
        }

        if (robot.status === "ERROR") {
            const recoverButton =
                document.createElement("button");

            recoverButton.type = "button";
            recoverButton.className =
                "robot-recover-button";

            recoverButton.textContent =
                "Robot 복구";

            recoverButton.addEventListener(
                "click",
                () => {
                    recoverRobot(
                        robot.robot_id,
                        recoverButton,
                    );
                },
            );

            card.appendChild(recoverButton);
        }

        robotList.appendChild(card);
    }
}

async function loadHistoryOperationExecutions(
    workExecutionId,
) {
    const select =
        document.getElementById(
            "history-operation-execution",
        );

    select.disabled = true;
    select.replaceChildren();

    const loadingOption =
        document.createElement("option");

    loadingOption.value = "";
    loadingOption.textContent =
        "Operation을 불러오는 중입니다.";

    select.appendChild(loadingOption);

    renderOperationSummary(null);

    try {
        const response = await fetch(
            `${WORK_EXECUTIONS_API_URL}/${workExecutionId}/operations`,
            {
                headers: {
                    "Accept": "application/json",
                },
            },
        );

        const responseData =
            await response.json();

        if (
            !response.ok
            || !responseData.success
        ) {
            throw new Error(
                responseData.error?.message
                ?? "Operation Execution 조회에 실패했습니다.",
            );
        }

        select.replaceChildren();

        const placeholder =
            document.createElement("option");

        placeholder.value = "";
        placeholder.textContent =
            "Operation Execution 선택";

        select.appendChild(placeholder);

        for (const execution of responseData.data) {
            const option =
                document.createElement("option");

            option.value = String(
                execution.operation_execution_id,
            );

            option.textContent = [
                `단계 ${execution.sequence}`,
                execution.operation?.name
                    ?? execution.operation?.code
                    ?? `Operation ${execution.operation_id}`,
                execution.status,
            ].join(" · ");

            option.dataset.operation =
                JSON.stringify(execution);

            select.appendChild(option);
        }

        select.disabled =
            responseData.data.length === 0;
    } catch (error) {
        console.error(
            "Failed to load operation executions:",
            error,
        );

        select.replaceChildren();

        const option =
            document.createElement("option");

        option.value = "";
        option.textContent =
            "Operation Execution 조회 실패";

        select.appendChild(option);
        select.disabled = true;
    }
}

function resetHistoryOperationSelect() {
    const select =
        document.getElementById(
            "history-operation-execution",
        );

    select.replaceChildren();

    const option =
        document.createElement("option");

    option.value = "";
    option.textContent =
        "Operation Execution 선택";

    select.appendChild(option);
    select.disabled = true;
}

async function recoverRobot(
    robotId,
    button,
) {
    const confirmed = window.confirm(
        `Robot ${robotId}을 복구하시겠습니까?`,
    );

    if (!confirmed) {
        return;
    }

    const originalText =
        button.textContent;

    button.disabled = true;
    button.textContent = "복구 중...";

    try {
        const response = await fetch(
            `/api/v1/robots/${robotId}/recover`,
            {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                },
            },
        );

        const responseData =
            await response.json();

        if (
            !response.ok
            || !responseData.success
        ) {
            throw new Error(
                responseData.error?.message
                ?? "Robot 복구에 실패했습니다.",
            );
        }

        await Promise.all([
            loadDashboard(false),
            loadSystemLogs(false),
        ]);
    } catch (error) {
        console.error(
            "Failed to recover robot:",
            error,
        );

        window.alert(error.message);

        button.disabled = false;
        button.textContent =
            originalText;
    }
}

function renderOperationSummary(execution) {
    const summary =
        document.getElementById(
            "history-operation-summary",
        );

    if (!execution) {
        summary.textContent =
            "Operation을 선택하면 실행 정보가 표시됩니다.";
        return;
    }

    summary.replaceChildren();

    summary.append(
        createDetail(
            "Operation Execution ID",
            execution.operation_execution_id,
        ),
        createDetail(
            "Sequence",
            execution.sequence,
        ),
        createDetail(
            "Operation",
            execution.operation?.name
                ?? execution.operation?.code
                ?? execution.operation_id,
        ),
        createDetail(
            "Status",
            execution.status,
        ),
        createDetail(
            "Start Time",
            execution.start_time ?? "-",
        ),
        createDetail(
            "End Time",
            execution.end_time ?? "-",
        ),
    );
}


function renderSuccessRate(summary) {
    const value =
        document.getElementById(
            "success-rate-value",
        );

    const bar =
        document.getElementById(
            "success-rate-bar",
        );

    const text =
        document.getElementById(
            "success-rate-summary",
        );

    const track =
        document.querySelector(
            ".success-rate-track",
        );

    const successRate = Number(
        summary?.success_rate ?? 0,
    );

    const safeRate = Math.min(
        100,
        Math.max(0, successRate),
    );

    value.textContent =
        `${safeRate.toFixed(1)}%`;

    bar.style.width = `${safeRate}%`;

    track.setAttribute(
        "aria-valuenow",
        String(safeRate),
    );

    if (!summary?.terminal_total) {
        text.textContent =
            "종료된 실행이 없습니다.";
        return;
    }

    text.textContent =
        `성공 ${summary.completed}`
        + ` · 실패 ${summary.failed}`
        + ` · 취소 ${summary.cancelled}`;
}

async function loadWorkOrderProgress(
    workOrderId,
) {
    const response = await fetch(
        `${WORK_ORDERS_API_URL}/${workOrderId}/progress`,
        {
            method: "GET",
            headers: {
                "Accept": "application/json",
            },
        },
    );

    const responseData =
        await response.json();

    if (
        !response.ok
        || !responseData.success
    ) {
        throw new Error(
            responseData.error?.message
            ?? "진행률 조회에 실패했습니다.",
        );
    }

    return responseData.data;
}

async function loadWorkOrders(
    showLoading = true,
) {
    const listElement = document.getElementById(
        "work-order-list",
    );

    const refreshButton = document.getElementById(
        "refresh-button",
    );

    if (showLoading) {
        listElement.textContent =
            "Work Order를 불러오는 중입니다.";
    }

    refreshButton.disabled = true;

    try {
        const response = await fetch(
            WORK_ORDERS_API_URL,
            {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            },
        );

        const responseData = await response.json();

        if (!response.ok || !responseData.success) {
            const errorMessage =
                responseData.error?.message
                ?? "Work Order 조회에 실패했습니다.";

            throw new Error(errorMessage);
        }

        const workOrdersWithProgress =
            await Promise.all(
                responseData.data.map(
                    async (workOrder) => {
                        try {
                            const progress =
                                await loadWorkOrderProgress(
                                    workOrder.work_order_id,
                                );

                            return {
                                ...workOrder,
                                progress,
                            };
                        } catch (error) {
                            console.error(
                                "Failed to load progress:",
                                error,
                            );

                            return {
                                ...workOrder,
                                progress: null,
                            };
                        }
                    },
                ),
            );

        renderWorkOrders(
            workOrdersWithProgress,
        );

        renderDashboardWorkOrders(
            workOrdersWithProgress,
        );

    } catch (error) {
        const dashboardList =
            document.getElementById(
                "dashboard-work-list",
            );

        dashboardList.textContent =
            "현재 작업을 불러오지 못했습니다.";

        console.error(
            "Failed to load work orders:",
            error,
        );

        renderError(
            "Work Order를 불러오지 못했습니다.",
        );
    } finally {
        refreshButton.disabled = false;
    }
}

function renderDashboardWorkOrders(
    workOrders,
) {
    const listElement =
        document.getElementById(
            "dashboard-work-list",
        );

    listElement.replaceChildren();

    if (!Array.isArray(workOrders)) {
        listElement.textContent =
            "올바르지 않은 Work Order 응답입니다.";
        return;
    }

    const actionableWorkOrders =
        workOrders.filter(
            (workOrder) =>
                workOrder.status === "READY"
                || workOrder.status === "RUNNING",
        );

    if (actionableWorkOrders.length === 0) {
        const emptyMessage =
            document.createElement("p");

        emptyMessage.className =
            "empty-message";

        emptyMessage.textContent =
            "시작 대기 또는 진행 중인 작업이 없습니다.";

        listElement.appendChild(
            emptyMessage,
        );

        return;
    }

    actionableWorkOrders.sort(
        (left, right) => {
            if (
                left.status === "RUNNING"
                && right.status !== "RUNNING"
            ) {
                return -1;
            }

            if (
                right.status === "RUNNING"
                && left.status !== "RUNNING"
            ) {
                return 1;
            }

            return (
                Number(left.priority ?? 999)
                - Number(right.priority ?? 999)
            );
        },
    );

    for (
        const workOrder
        of actionableWorkOrders
    ) {
        const card =
            createDashboardWorkCard(
                workOrder,
            );

        listElement.appendChild(card);
    }
}

function createDashboardWorkCard(workOrder) {
    const card =
        document.createElement("article");

    card.className =
        "dashboard-work-card";

    card.dataset.status =
        workOrder.status;

    const header =
        document.createElement("div");

    header.className =
        "dashboard-work-card-header";

    const titleArea =
        document.createElement("div");

    const orderNumber =
        document.createElement("span");

    orderNumber.className =
        "order-number";

    orderNumber.textContent =
        workOrder.order_number ?? "-";

    const title =
        document.createElement("h3");

    title.textContent =
        workOrder.title ?? "-";

    titleArea.append(
        orderNumber,
        title,
    );

    const status =
        document.createElement("span");

    status.className = "status-badge";
    status.dataset.status =
        workOrder.status;

    status.textContent =
        workOrder.status;

    header.append(
        titleArea,
        status,
    );

    const information =
        document.createElement("div");

    information.className =
        "dashboard-work-information";

    information.append(
        createDetail(
            "Work Order ID",
            workOrder.work_order_id,
        ),
        createDetail(
            "Priority",
            workOrder.priority,
        ),
        createDetail(
            "진행",
            workOrder.progress?.progress
                ?? "0/0",
        ),
    );

    if (
        workOrder.progress
            ?.current_operation
    ) {
        const operation =
            workOrder.progress
                .current_operation;

        information.append(
            createDetail(
                "현재 Operation",
                [
                    `단계 ${operation.sequence}`,
                    operation.name
                        ?? operation.code
                        ?? operation.operation_id,
                    operation.status,
                ].join(" · "),
            ),
        );
    }

    const controls =
        document.createElement("div");

    controls.className =
        "dashboard-work-actions";

    if (workOrder.status === "RUNNING") {
        const stopButton =
            document.createElement("button");

        stopButton.type = "button";

        stopButton.className =
            "dashboard-action-button danger-button";

        stopButton.textContent =
            "작업 중지";

        stopButton.addEventListener(
            "click",
            () => {
                handleWorkStop(
                    workOrder.work_order_id,
                    stopButton,
                );
            },
        );

        controls.appendChild(stopButton);
    }

    if (workOrder.status === "READY") {
        appendDashboardStartControls(
            controls,
            workOrder,
        );
    }

    card.append(
        header,
        information,
        controls,
    );

    return card;
}

function appendDashboardStartControls(
    controls,
    workOrder,
) {
    const robotSelect =
        document.createElement("select");

    robotSelect.className =
        "dashboard-robot-select";

    robotSelect.setAttribute(
        "aria-label",
        "작업에 사용할 Robot 선택",
    );

    const idleRobots =
        dashboardRobots.filter(
            (robot) =>
                robot.status === "IDLE",
        );

    const placeholder =
        document.createElement("option");

    placeholder.value = "";
    placeholder.selected = true;
    placeholder.disabled = true;

    placeholder.textContent =
        idleRobots.length > 0
            ? "Robot을 선택하세요"
            : "사용 가능한 Robot 없음";

    robotSelect.appendChild(
        placeholder,
    );

    for (const robot of idleRobots) {
        const option =
            document.createElement("option");

        option.value =
            String(robot.robot_id);

        option.textContent = [
            `Robot ${robot.robot_id}`,
            robot.name ?? robot.robot_code,
        ]
            .filter(Boolean)
            .join(" · ");

        robotSelect.appendChild(option);
    }

    const startButton =
        document.createElement("button");

    startButton.type = "button";

    startButton.className =
        "dashboard-action-button";

    startButton.textContent =
        "작업 시작";

    startButton.disabled = true;

    robotSelect.addEventListener(
        "change",
        () => {
            startButton.disabled =
                !robotSelect.value;
        },
    );

    startButton.addEventListener(
        "click",
        () => {
            handleWorkExecution(
                workOrder.work_order_id,
                Number(robotSelect.value),
                startButton,
                robotSelect,
            );
        },
    );

    controls.append(
        robotSelect,
        startButton,
    );
}

function renderWorkOrders(workOrders) {
    const listElement = document.getElementById(
        "work-order-list",
    );

    listElement.replaceChildren();

    if (!Array.isArray(workOrders)) {
        renderError(
            "올바르지 않은 Work Order 응답입니다.",
        );
        return;
    }

    if (workOrders.length === 0) {
        const emptyMessage =
            document.createElement("p");

        emptyMessage.className = "empty-message";
        emptyMessage.textContent =
            "등록된 Work Order가 없습니다.";

        listElement.appendChild(emptyMessage);
        return;
    }

    for (const workOrder of workOrders) {
        const card = createWorkOrderCard(workOrder);

        listElement.appendChild(card);
    }
}


function createWorkOrderCard(workOrder) {
    const card = document.createElement("article");
    card.className = "work-order-card";

    const cardHeader = document.createElement("div");
    cardHeader.className = "work-order-card-header";

    const titleArea = document.createElement("div");

    const orderNumber = document.createElement("p");
    orderNumber.className = "order-number";
    orderNumber.textContent =
        workOrder.order_number ?? "-";

    const title = document.createElement("h3");
    title.textContent = workOrder.title ?? "-";

    titleArea.append(orderNumber, title);

    const status = document.createElement("span");
    status.className = "status-badge";
    status.dataset.status = workOrder.status;
    status.textContent = workOrder.status ?? "UNKNOWN";

    cardHeader.append(titleArea, status);

    const details = document.createElement("div");
    details.className = "work-order-details";

    details.append(
        createDetail(
            "Work Order ID",
            workOrder.work_order_id,
        ),
        createDetail(
            "Installation ID",
            workOrder.installation_id,
        ),
        createDetail(
            "Priority",
            workOrder.priority,
        ),
        createDetail(
            "Created By",
            workOrder.created_by ?? "-",
        ),
    );

    const remark = document.createElement("p");
    remark.className = "work-order-remark";
    remark.textContent =
        workOrder.remark ?? "비고 없음";

    const progressSection =
        createProgressSection(workOrder);

    const actions = createWorkOrderActions(
        workOrder,
    );

    card.append(
        cardHeader,
        details,
        remark,
        progressSection,
        actions,
    );

    return card;
}

function createProgressSection(workOrder) {
    const section =
        document.createElement("div");

    section.className =
        "work-order-progress";

    const progress = workOrder.progress;

    if (!progress) {
        section.textContent =
            "진행 정보를 불러올 수 없습니다.";

        return section;
    }

    const summary =
        document.createElement("div");

    summary.className =
        "progress-summary";

    const label =
        document.createElement("span");

    label.textContent = "Operation 진행";

    const value =
        document.createElement("strong");

    value.textContent =
        progress.progress ?? "0/0";

    summary.append(label, value);

    section.appendChild(summary);

    if (progress.current_operation) {
        const current =
            document.createElement("p");

        current.className =
            "current-operation";

        const operation =
            progress.current_operation;

        current.textContent = [
            `현재 단계 ${operation.sequence}`,
            operation.name
                ?? operation.code
                ?? `Operation ${operation.operation_id}`,
            `(${operation.status})`,
        ].join(" · ");

        section.appendChild(current);
    }

    return section;
}

function createDetail(label, value) {
    const wrapper = document.createElement("div");
    wrapper.className = "work-order-detail";

    const labelElement =
        document.createElement("span");

    labelElement.className = "detail-label";
    labelElement.textContent = label;

    const valueElement =
        document.createElement("span");

    valueElement.className = "detail-value";
    valueElement.textContent = value ?? "-";

    wrapper.append(
        labelElement,
        valueElement,
    );

    return wrapper;
}

function renderError(message) {
    const listElement = document.getElementById(
        "work-order-list",
    );

    listElement.replaceChildren();

    const errorMessage =
        document.createElement("p");

    errorMessage.className = "error-message";
    errorMessage.textContent = message;

    listElement.appendChild(errorMessage);
}

async function handleWorkOrderSubmit(event) {
    event.preventDefault();

    const form = event.currentTarget;

    const createButton = document.getElementById(
        "create-button",
    );

    const formMessage = document.getElementById(
        "form-message",
    );

    const formData = new FormData(form);

    const requestData = {
        order_number: formData
            .get("order_number")
            .trim(),

        title: formData
            .get("title")
            .trim(),

        installation_id: Number(
            formData.get("installation_id"),
        ),

        priority: Number(
            formData.get("priority"),
        ),

        remark: formData
            .get("remark")
            .trim(),

        created_by: formData
            .get("created_by")
            .trim(),
    };

    createButton.disabled = true;

    setFormMessage(
        "Work Order를 생성하는 중입니다.",
        "",
    );

    try {
        const response = await fetch(
            WORK_ORDERS_API_URL,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify(requestData),
            },
        );

        const responseData = await response.json();

        if (!response.ok || !responseData.success) {
            const errorMessage =
                responseData.error?.message
                ?? "Work Order 생성에 실패했습니다.";

            throw new Error(errorMessage);
        }

        setFormMessage(
            `Work Order ${responseData.data.order_number}가 생성됐습니다.`,
            "success",
        );

        form.reset();

        document.getElementById(
            "priority",
        ).value = "3";

        await loadWorkOrders();
        closeWorkOrderModal();
    } catch (error) {
        console.error(
            "Failed to create work order:",
            error,
        );

        setFormMessage(
            error.message,
            "error",
        );
    } finally {
        createButton.disabled = false;
    }
}

function setFormMessage(message, type) {
    const formMessage = document.getElementById(
        "form-message",
    );

    formMessage.textContent = message;
    formMessage.className = type;
}

function createWorkOrderActions(workOrder) {
    const actions =
        document.createElement("div");

    actions.className =
        "work-order-actions";

    if (workOrder.status === "CREATED") {
        const button =
            document.createElement("button");

        button.type = "button";
        button.textContent = "작업 준비";

        button.addEventListener(
            "click",
            () => handleStatusUpdate(
                workOrder.work_order_id,
                "READY",
                button,
            ),
        );

        actions.appendChild(button);

        return actions;
    }

    if (workOrder.status === "READY") {
        const robotSelect =
            document.createElement("select");

        robotSelect.className =
            "robot-id-input";

        robotSelect.setAttribute(
            "aria-label",
            "Robot 선택",
        );

        const idleRobots =
            dashboardRobots.filter(
                (robot) =>
                    robot.status === "IDLE",
            );

        const placeholder =
            document.createElement("option");

        placeholder.value = "";

        placeholder.textContent =
            idleRobots.length > 0
                ? "Robot 선택"
                : "사용 가능한 Robot 없음";

        placeholder.selected = true;
        placeholder.disabled = true;

        robotSelect.appendChild(placeholder);

        for (const robot of idleRobots) {
            const option =
                document.createElement("option");

            option.value =
                String(robot.robot_id);

            option.textContent = [
                `Robot ${robot.robot_id}`,
                robot.name ?? robot.robot_code,
                robot.status,
            ]
                .filter(Boolean)
                .join(" · ");

            robotSelect.appendChild(option);
        }

        const button =
            document.createElement("button");

        button.type = "button";
        button.textContent = "작업 시작";
        button.disabled =
            idleRobots.length === 0;

        robotSelect.addEventListener(
            "change",
            () => {
                button.disabled =
                    !robotSelect.value;
            },
        );

        button.addEventListener(
            "click",
            () => {
                handleWorkExecution(
                    workOrder.work_order_id,
                    Number(robotSelect.value),
                    button,
                    robotSelect,
                );
            },
        );

        actions.append(
            robotSelect,
            button,
        );

        return actions;
    }

    if (workOrder.status === "RUNNING") {
        const stateMessage =
            document.createElement("span");

        stateMessage.className =
            "action-state-message";

        stateMessage.textContent =
            "작업 실행 중";

        const stopButton =
            document.createElement("button");

        stopButton.type = "button";
        stopButton.className =
            "danger-button";

        stopButton.textContent =
            "작업 중지";

        stopButton.addEventListener(
            "click",
            () => {
                handleWorkStop(
                    workOrder.work_order_id,
                    stopButton,
                );
            },
        );

        actions.append(
            stateMessage,
            stopButton,
        );

        return actions;
    }

    const message =
        document.createElement("span");

    message.className =
        "action-state-message";

    const messages = {
        RUNNING: "작업 실행 중",
        COMPLETED: "작업 완료",
        FAILED: "작업 실패",
        CANCELLED: "작업 취소됨",
    };

    message.textContent =
        messages[workOrder.status]
        ?? workOrder.status
        ?? "상태 없음";

    actions.appendChild(message);

    return actions;
}

async function handleWorkStop(
    workOrderId,
    stopButton,
) {
    const confirmed = window.confirm(
        "현재 로봇 동작을 강제로 중지하시겠습니까?",
    );

    if (!confirmed) {
        return;
    }

    const originalText =
        stopButton.textContent;

    stopButton.disabled = true;
    stopButton.textContent =
        "중지 요청 중...";

    try {
        const response = await fetch(
            `${WORK_ORDERS_API_URL}/${workOrderId}/stop`,
            {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                },
            },
        );

        const responseData =
            await response.json();

        if (
            !response.ok
            || !responseData.success
        ) {
            throw new Error(
                responseData.error?.message
                ?? "작업 중지 요청에 실패했습니다.",
            );
        }

        stopButton.textContent =
            "취소 결과 대기 중...";

        await Promise.all([
            loadWorkOrders(false),
            loadDashboard(false),
            loadSystemLogs(false),
        ]);
    } catch (error) {
        console.error(
            "Failed to stop work order:",
            error,
        );

        window.alert(error.message);

        stopButton.disabled = false;
        stopButton.textContent =
            originalText;
    }
}

async function handleStatusUpdate(
    workOrderId,
    status,
    saveButton,
) {
    const originalButtonText =
        saveButton.textContent;

    saveButton.disabled = true;
    saveButton.textContent = "저장 중...";

    try {
        const response = await fetch(
            `${WORK_ORDERS_API_URL}/${workOrderId}`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    status: status,
                }),
            },
        );

        const responseData = await response.json();

        if (!response.ok || !responseData.success) {
            const errorMessage =
                responseData.error?.message
                ?? "상태 변경에 실패했습니다.";

            throw new Error(errorMessage);
        }

        await loadWorkOrders();
    } catch (error) {
        console.error(
            "Failed to update work order:",
            error,
        );

        window.alert(error.message);
    } finally {
        saveButton.disabled = false;
        saveButton.textContent =
            originalButtonText;
    }
}

async function handleWorkExecution(
    workOrderId,
    robotId,
    button,
    robotInput,
) {
    if (
        !Number.isInteger(robotId)
        || robotId <= 0
    ) {
        window.alert(
            "Robot ID는 양의 정수여야 합니다.",
        );
        return;
    }

    const originalText =
        button.textContent;

    button.disabled = true;
    robotInput.disabled = true;
    button.textContent = "접수 중...";

    try {
        const response = await fetch(
            `${WORK_ORDERS_API_URL}/${workOrderId}/execute`,
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json",
                    "Accept":
                        "application/json",
                },
                body: JSON.stringify({
                    robot_id: robotId,
                }),
            },
        );

        const responseData =
            await response.json();

        if (
            !response.ok
            || !responseData.success
        ) {
            throw new Error(
                responseData.error?.message
                ?? "작업 시작에 실패했습니다.",
            );
        }

        await loadWorkOrders(false);
    } catch (error) {
        console.error(
            "Failed to execute work order:",
            error,
        );

        window.alert(error.message);

        button.disabled = false;
        robotInput.disabled = false;
        button.textContent =
            originalText;
    }
}

async function loadRecentLogs(
    showLoading = true,
) {
    const listElement =
        document.getElementById(
            "recent-log-list",
        );

    if (showLoading) {
        listElement.textContent =
            "최근 로그를 불러오는 중입니다.";
    }

    try {
        const response = await fetch(
            `${LOGS_API_URL}?limit=5`,
            {
                headers: {
                    "Accept": "application/json",
                },
            },
        );

        const responseData =
            await response.json();

        if (
            !response.ok
            || !responseData.success
        ) {
            throw new Error(
                responseData.error?.message
                ?? "최근 로그 조회에 실패했습니다.",
            );
        }

        renderRecentLogs(
            responseData.data,
        );
    } catch (error) {
        console.error(
            "Failed to load recent logs:",
            error,
        );

        listElement.textContent =
            "최근 로그를 불러오지 못했습니다.";
    }
}

async function loadSystemLogs(
    showLoading = true,
) {
    const listElement =
        document.getElementById(
            "history-list",
        );

    const refreshButton =
        document.getElementById(
            "history-refresh-button",
        );

    if (showLoading) {
        listElement.textContent =
            "로그를 불러오는 중입니다.";
    }

    refreshButton.disabled = true;

    try {
        const query =
            new URLSearchParams({
                limit: "100",
            });

        if (selectedHistoryOperationExecutionId) {
            query.set(
                "operation_execution_id",
                String(
                    selectedHistoryOperationExecutionId,
                ),
            );
        } else if (selectedHistoryWorkExecutionId) {
            query.set(
                "work_execution_id",
                String(
                    selectedHistoryWorkExecutionId,
                ),
            );
        }

        const response = await fetch(
            `${LOGS_API_URL}?${query.toString()}`,
            {
                headers: {
                    "Accept": "application/json",
                },
            },
        );

        const responseData =
            await response.json();

        if (
            !response.ok
            || !responseData.success
        ) {
            throw new Error(
                responseData.error?.message
                ?? "로그 조회에 실패했습니다.",
            );
        }

        renderSystemLogs(responseData.data);

    } catch (error) {
        console.error(
            "Failed to load system logs:",
            error,
        );

        listElement.textContent =
            "로그를 불러오지 못했습니다.";

    } finally {
        refreshButton.disabled = false;
    }
}

function renderRecentLogs(logs) {
    const listElement =
        document.getElementById(
            "recent-log-list",
        );

    listElement.replaceChildren();

    if (
        !Array.isArray(logs)
        || logs.length === 0
    ) {
        const emptyMessage =
            document.createElement("p");

        emptyMessage.className =
            "empty-message";

        emptyMessage.textContent =
            "저장된 로그가 없습니다.";

        listElement.appendChild(
            emptyMessage,
        );

        return;
    }

    for (const log of logs.slice(0, 5)) {
        const item =
            document.createElement("article");

        item.className = "recent-log-item";
        item.dataset.severity =
            log.severity ?? "INFO";

        const code =
            document.createElement("strong");

        code.textContent =
            log.code
            ?? log.log_type
            ?? "LOG";

        const message =
            document.createElement("span");

        message.textContent =
            log.message ?? "-";

        const timestamp =
            document.createElement("time");

        timestamp.textContent =
            formatLogTimestamp(
                log.timestamp,
            );

        item.append(
            code,
            message,
            timestamp,
        );

        listElement.appendChild(item);
    }
}

function renderSystemLogs(logs) {
    const listElement =
        document.getElementById(
            "history-list",
        );

    listElement.replaceChildren();

    if (!Array.isArray(logs)) {
        listElement.textContent =
            "올바르지 않은 로그 응답입니다.";
        return;
    }

    if (logs.length === 0) {
        listElement.textContent =
            "저장된 로그가 없습니다.";
        return;
    }

    for (const log of logs) {
        const item =
            document.createElement("article");

        item.className = "history-item";
        item.dataset.severity =
            log.severity ?? "INFO";

        const header =
            document.createElement("div");

        header.className = "history-header";

        const code =
            document.createElement("strong");

        code.textContent =
            log.code ?? log.log_type ?? "LOG";

        const timestamp =
            document.createElement("time");

        timestamp.textContent =
            formatLogTimestamp(log.timestamp);

        header.append(code, timestamp);

        const message =
            document.createElement("p");

        message.textContent =
            log.message ?? "-";

        const metadata =
            document.createElement("small");

        metadata.textContent = [
            log.log_type,
            log.severity,
            log.robot_id
                ? `Robot ${log.robot_id}`
                : null,
            log.operation_execution_id
                ? `Operation Execution ${log.operation_execution_id}`
                : null,
        ].filter(Boolean).join(" · ");

        item.append(
            header,
            message,
            metadata,
        );

        listElement.appendChild(item);
    }
}

function formatLogTimestamp(value) {
    if (!value) {
        return "-";
    }

    const timestamp = new Date(value);

    if (Number.isNaN(timestamp.getTime())) {
        return value;
    }

    return timestamp.toLocaleString("ko-KR");
}

async function loadActiveInstallations(showLoading = true) {
    const list = document.getElementById("active-installation-list");

    if (showLoading) {
        list.textContent = "Installation Target을 불러오는 중입니다.";
    }

    try {
        const response = await fetch(ACTIVE_INSTALLATIONS_API_URL, {
            method: "GET",
            headers: {"Accept": "application/json"},
        });
        const responseData = await response.json();

        if (!response.ok || !responseData.success) {
            throw new Error(responseData.error?.message
                ?? "Installation Target 조회에 실패했습니다.");
        }

        renderActiveInstallations(responseData.data);
    } catch (error) {
        list.className = "error-message";
        list.textContent = "Installation Target을 불러오지 못했습니다.";
        console.error("Failed to load active installations:", error);
    }
}

function renderActiveInstallations(installations) {
    const list = document.getElementById("active-installation-list");
    list.replaceChildren();
    list.className = "active-installation-list";

    if (!Array.isArray(installations)) {
        list.className = "error-message";
        list.textContent = "올바르지 않은 Installation Target 응답입니다.";
        return;
    }

    if (installations.length === 0) {
        const emptyMessage = document.createElement("p");
        emptyMessage.className = "empty-message";
        emptyMessage.textContent =
            "현재 ACTIVE 상태인 Installation Target이 없습니다.";
        list.appendChild(emptyMessage);
        return;
    }

    for (const installation of installations) {
        const card = document.createElement("article");
        card.className = "installation-target-card";

        const header = document.createElement("div");
        header.className = "work-order-card-header";
        const titleArea = document.createElement("div");
        const targetCode = document.createElement("p");
        targetCode.className = "order-number";
        targetCode.textContent = installation.target_code ?? "-";
        const targetName = document.createElement("h3");
        targetName.textContent = installation.target_name ?? "-";
        titleArea.append(targetCode, targetName);

        const status = document.createElement("span");
        status.className = "status-badge";
        status.dataset.status = installation.status;
        status.textContent = installation.status ?? "UNKNOWN";
        header.append(titleArea, status);

        const details = document.createElement("div");
        details.className = "work-order-details";
        details.append(
            createDetail("Project", installation.project_name ?? "-"),
            createDetail("Project Code", installation.project_code ?? "-"),
            createDetail("Site", installation.site_name ?? "-"),
            createDetail("Installation ID", installation.installation_id),
        );

        card.append(header, details);
        list.appendChild(card);
    }
}
