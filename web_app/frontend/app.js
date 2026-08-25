"use strict";

const WORK_ORDER_POLL_INTERVAL_MS = 3000;
const LOGS_API_URL = "/api/v1/logs";
const DASHBOARD_API_URL =
    "/api/v1/dashboard";

const WORK_ORDERS_API_URL =
    "/api/v1/work-orders";

document.addEventListener(
    "DOMContentLoaded",
    () => {
        initializeNavigation();
        initializeWorkOrderModal();

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

        refreshButton.addEventListener(
            "click",
            () => loadWorkOrders(true),
        );

        historyRefreshButton.addEventListener(
            "click",
            () => loadSystemLogs(true),
        );

        workOrderForm.addEventListener(
            "submit",
            handleWorkOrderSubmit,
        );

        loadWorkOrders();
        loadSystemLogs();
        loadDashboard();

        window.setInterval(
            () => {
                loadWorkOrders(false);
                loadSystemLogs(false);
                loadDashboard(false);
            },
            WORK_ORDER_POLL_INTERVAL_MS,
        );
    },
);

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

function initializeWorkOrderModal() {
    const openButton =
        document.getElementById(
            "open-work-order-modal",
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

    openButton.addEventListener(
        "click",
        openWorkOrderModal,
    );

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

        renderRobots(
            responseData.data?.robots,
        );

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

        robotList.appendChild(card);
    }
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

    } catch (error) {
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
        const robotInput =
            document.createElement("input");

        robotInput.type = "number";
        robotInput.min = "1";
        robotInput.value = "1";
        robotInput.className =
            "robot-id-input";

        const button =
            document.createElement("button");

        button.type = "button";
        button.textContent = "작업 시작";

        button.addEventListener(
            "click",
            () => handleWorkExecution(
                workOrder.work_order_id,
                Number(robotInput.value),
                button,
                robotInput,
            ),
        );

        actions.append(
            robotInput,
            button,
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
        const response = await fetch(
            `${LOGS_API_URL}?limit=100`,
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