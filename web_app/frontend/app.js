const WORK_ORDER_STATUSES = [
    "CREATED",
    "READY",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
];

"use strict";

const WORK_ORDERS_API_URL = "/api/v1/work-orders";

document.addEventListener("DOMContentLoaded", () => {
    const refreshButton = document.getElementById(
        "refresh-button",
    );

    const workOrderForm = document.getElementById(
        "work-order-form",
    );

    refreshButton.addEventListener(
        "click",
        loadWorkOrders,
    );

    workOrderForm.addEventListener(
        "submit",
        handleWorkOrderSubmit,
    );

    loadWorkOrders();
});


async function loadWorkOrders() {
    const listElement = document.getElementById(
        "work-order-list",
    );

    const refreshButton = document.getElementById(
        "refresh-button",
    );

    listElement.textContent =
        "Work Order를 불러오는 중입니다.";

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

        renderWorkOrders(responseData.data);
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

    const actions = createWorkOrderActions(
        workOrder,
    );

    card.append(
        cardHeader,
        details,
        remark,
        actions,
    );


    return card;
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
    const actions = document.createElement("div");
    actions.className = "work-order-actions";

    const statusSelect =
        document.createElement("select");

    statusSelect.setAttribute(
        "aria-label",
        "Work Order 상태",
    );

    for (const status of WORK_ORDER_STATUSES) {
        const option =
            document.createElement("option");

        option.value = status;
        option.textContent = status;
        option.selected =
            status === workOrder.status;

        statusSelect.appendChild(option);
    }

    const saveButton =
        document.createElement("button");

    saveButton.type = "button";
    saveButton.textContent = "상태 저장";

    saveButton.addEventListener(
        "click",
        async () => {
            await handleStatusUpdate(
                workOrder.work_order_id,
                statusSelect.value,
                saveButton,
            );
        },
    );

    actions.append(
        statusSelect,
        saveButton,
    );

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
