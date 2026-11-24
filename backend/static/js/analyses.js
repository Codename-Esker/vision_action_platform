const form = document.querySelector("#analysis-form");
const mode = document.querySelector("#input-type");
const video = document.querySelector("#video");
const camera = document.querySelector("#camera");
const submitButton = document.querySelector("#submit-job");
const formMessage = document.querySelector("#form-message");
const statusText = document.querySelector("#job-status");
const detailText = document.querySelector("#job-detail");
const table = document.querySelector("#result-table");
const resultBody = document.querySelector("#result-body");
const historyList = document.querySelector("#history");

const statusLabels = {
    PENDING: "대기 중",
    STARTED: "처리 중",
    SUCCESS: "완료",
    FAILURE: "실패",
};

const actionLabels = {
    bend_return: "몸 굽혔다 펴기",
    drink_return: "마시고 돌아오기",
    leg_raise_lower: "다리 들었다 내리기",
    sit_stand: "앉았다 일어서기",
    walk_turn_walk: "걷고 돌아서 걷기",
    wave: "손 흔들기",
};

let selection = 0;
let timer;

function updateInputs() {
    const isCamera = mode.value === "camera";
    document.querySelector("#upload-fields").hidden = isCamera;
    document.querySelector("#camera-fields").hidden = !isCamera;
    video.disabled = isCamera;
    video.required = !isCamera;
    camera.disabled = !isCamera;
}

async function readJson(response) {
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
        throw new Error(`서버 응답을 확인해 주세요. HTTP ${response.status}`);
    }

    const data = await response.json();
    if (!response.ok) {
        const message = Object.values(data).flat().join(" ");
        throw new Error(message || `요청 실패: HTTP ${response.status}`);
    }
    return data;
}

function updateHistory(job) {
    let button = historyList.querySelector(`[data-job-id="${job.id}"]`);
    if (!button) {
        document.querySelector("#empty-history")?.remove();
        const item = document.createElement("li");
        button = document.createElement("button");
        button.type = "button";
        button.dataset.jobId = job.id;
        item.append(button);
        historyList.prepend(item);
        if (historyList.children.length > 10) {
            historyList.lastElementChild.remove();
        }
    }

    const input = job.input_type === "camera" ? "IP Webcam" : "영상 업로드";
    button.textContent = `#${job.id} · ${input} · ${statusLabels[job.status]}`;
}

function showResult(job) {
    updateHistory(job);
    statusText.textContent = `작업 #${job.id} · ${statusLabels[job.status]}`;
    detailText.textContent = "";
    resultBody.replaceChildren();
    table.hidden = true;

    if (job.status === "FAILURE") {
        detailText.textContent = job.error_message || "분석 중 오류가 발생했습니다.";
        return;
    }
    if (job.status !== "SUCCESS") return;

    const predictions = job.predictions || [];
    const seconds = job.processing_seconds;
    const timing = seconds == null ? "" : ` · AI 처리 ${seconds}초`;
    detailText.textContent = predictions.length
        ? `추적 ID ${predictions.length}개${timing}`
        : `예측에 필요한 유효 프레임이 확보된 사람이 없습니다${timing}`;

    for (const person of predictions) {
        const row = resultBody.insertRow();
        row.insertCell().textContent = person.track_id;
        row.insertCell().textContent = actionLabels[person.action_label] || person.action_label;
        row.insertCell().textContent = `${(person.confidence * 100).toFixed(1)}%`;
    }
    table.hidden = predictions.length === 0;
}

function selectJob(id) {
    clearTimeout(timer);
    const current = ++selection;
    statusText.textContent = `작업 #${id} 조회 중`;
    detailText.textContent = "";
    table.hidden = true;

    async function refresh() {
        try {
            const response = await fetch(`${form.action}${id}/`, {
                headers: { Accept: "application/json" },
                cache: "no-store",
            });
            const job = await readJson(response);
            if (current !== selection) return;

            showResult(job);
            if (job.status === "PENDING" || job.status === "STARTED") {
                timer = setTimeout(refresh, 1500);
            }
        } catch (error) {
            if (current === selection) {
                statusText.textContent = `작업 #${id} 조회 실패`;
                detailText.textContent = error.message;
            }
        }
    }
    refresh();
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submitButton.disabled = true;
    formMessage.textContent = "분석 요청을 보내는 중입니다.";

    try {
        const response = await fetch(form.action, {
            method: "POST",
            headers: {
                Accept: "application/json",
                "X-CSRFToken": form.elements.csrfmiddlewaretoken.value,
            },
            body: new FormData(form),
        });
        const job = await readJson(response);
        updateHistory(job);
        formMessage.textContent = `작업 #${job.id}이 접수됐습니다.`;
        selectJob(job.id);
    } catch (error) {
        formMessage.textContent = `접수 실패 · ${error.message}`;
    } finally {
        submitButton.disabled = false;
    }
});

historyList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-job-id]");
    if (button) selectJob(button.dataset.jobId);
});

mode.addEventListener("change", updateInputs);
updateInputs();
