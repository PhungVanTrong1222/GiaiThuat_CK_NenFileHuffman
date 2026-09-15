/* Điều khiển giao diện: chọn file -> gửi API -> hiển thị và tải kết quả.
   JavaScript không thực hiện thuật toán Huffman; phần đó chạy trong Python. */

const fileInput = document.getElementById("file-input");
const compressButton = document.getElementById("compress-mode");
const decompressButton = document.getElementById("decompress-mode");
const submitButton = document.getElementById("submit-button");
const submitLabel = document.getElementById("submit-label");
const statusMessage = document.getElementById("status-message");
const dropZone = document.getElementById("drop-zone");
const removeButton = document.getElementById("remove-file");
const downloadLink = document.getElementById("download-link");

let currentMode = "compress";
let selectedFile = null;
let resultUrl = null;
let isProcessing = false;
let configuration = null;

// Đổi số byte thành chuỗi dung lượng dùng hệ số 1024.
function formatSize(bytes) {
    if (bytes < 1024) {
        return bytes + " B";
    }
    if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(2) + " KiB";
    }
    return (bytes / (1024 * 1024)).toFixed(2) + " MiB";
}

// Hiển thị trạng thái; dùng textContent để tên file/nội dung lỗi không thành HTML.
function showStatus(message, isError = false) {
    statusMessage.textContent = message;
    statusMessage.classList.toggle("error", isError);
}

// Giải phóng dữ liệu tải xuống cũ khi chọn file khác hoặc đổi chế độ.
function clearResult() {
    if (resultUrl !== null) {
        URL.revokeObjectURL(resultUrl);
        resultUrl = null;
    }
    downloadLink.removeAttribute("href");
    downloadLink.removeAttribute("download");
    document.getElementById("result-content").hidden = true;
    document.getElementById("empty-result").hidden = false;
    // Reset biểu đồ
    var originalFill = document.getElementById("original-bar-fill");
    var compressedFill = document.getElementById("compressed-bar-fill");
    if (originalFill) { originalFill.style.width = "0%"; }
    if (compressedFill) { compressedFill.style.width = "0%"; }
    var badge = document.getElementById("chart-saving-badge");
    if (badge) { badge.textContent = ""; badge.hidden = true; }
}

// Khóa các thao tác thay đổi đầu vào trong lúc chờ API.
function updateControls() {
    let unavailable = isProcessing || configuration === null;
    fileInput.disabled = unavailable;
    compressButton.disabled = isProcessing;
    decompressButton.disabled = isProcessing;
    removeButton.disabled = isProcessing;
    submitButton.disabled = unavailable || selectedFile === null;
    document.getElementById("file-form").setAttribute("aria-busy", String(isProcessing));

    if (isProcessing) {
        submitLabel.textContent = "Đang xử lý…";
    } else if (currentMode === "compress") {
        submitLabel.textContent = "Nén file";
    } else {
        submitLabel.textContent = "Giải nén file";
    }
}

// Xóa file đang chọn và số liệu liên quan để không tải nhầm kết quả cũ.
function clearSelection() {
    selectedFile = null;
    fileInput.value = "";
    document.getElementById("selected-file").hidden = true;
    clearResult();
    updateControls();
}

// Nhận một File từ hộp chọn hoặc thao tác kéo thả; kiểm tra dung lượng trước upload.
function selectFile(file) {
    if (isProcessing || configuration === null) {
        return;
    }
    clearSelection();
    if (!file) {
        showStatus("Chọn một file để bắt đầu.");
        return;
    }
    let sizeLimit = configuration.max_file_size;
    if (currentMode === "decompress") {
        sizeLimit = configuration.max_compressed_size;
    }
    if (file.size > sizeLimit) {
        showStatus("Dung lượng file vượt quá giới hạn tối đa cho phép (" + formatSize(sizeLimit) + ").", true);
        return;
    }
    selectedFile = file;
    document.getElementById("selected-file").hidden = false;
    document.getElementById("selected-name").textContent = file.name;
    document.getElementById("selected-size").textContent = formatSize(file.size);
    showStatus("File đã sẵn sàng. Bấm nút để xử lý.");
    updateControls();
}

// Cập nhật tiêu đề và hướng dẫn theo chế độ. Xóa file cũ để tránh gửi nhầm.
function changeMode(mode) {
    if (isProcessing) {
        return;
    }
    currentMode = mode;
    clearSelection();
    const isCompressMode = mode === "compress";
    compressButton.classList.toggle("active", isCompressMode);
    decompressButton.classList.toggle("active", !isCompressMode);
    compressButton.setAttribute("aria-pressed", String(isCompressMode));
    decompressButton.setAttribute("aria-pressed", String(!isCompressMode));
    if (isCompressMode) {
        document.getElementById("input-title").textContent = "Chọn file cần nén";
        document.getElementById("empty-description").textContent = "Chọn một file để xem dung lượng và kết quả sau khi nén.";
    } else {
        document.getElementById("input-title").textContent = "Chọn file cần giải nén";
        document.getElementById("empty-description").textContent = "Chọn file do ShrinkIT tạo để khôi phục dữ liệu gốc.";
    }
    updateFileHint();
    if (configuration !== null) {
        showStatus("Chọn một file để bắt đầu.");
    }
}

// Cập nhật hướng dẫn theo chế độ (đúng định dạng dự án hỗ trợ, không ghi cứng số MB).
function updateFileHint() {
    if (currentMode === "compress") {
        document.getElementById("file-hint").textContent = "Định dạng hỗ trợ: .txt, .csv, .log, .json";
        fileInput.accept = ".txt,.csv,.log,.json";
    } else {
        document.getElementById("file-hint").textContent = "Định dạng hỗ trợ: .bin (do ShrinkIT tạo)";
        fileInput.accept = ".bin";
    }
}

// Lấy cấu hình ứng dụng một lần khi trang mở. Nếu mất kết nối thì chặn upload.
async function loadConfiguration() {
    try {
        const response = await fetch("/api/config");
        if (!response.ok) {
            throw new Error("Không lấy được cấu hình.");
        }
        configuration = await response.json();
        updateFileHint();
        showStatus("Chọn một file để bắt đầu.");
    } catch (error) {
        configuration = null;
        document.getElementById("file-hint").textContent = "Chưa kết nối được đến server.";
        showStatus("Không kết nối được ứng dụng. Kiểm tra server rồi tải lại trang.", true);
    }
    updateControls();
}

// Đọc tên tải xuống do API đặt trong Content-Disposition.
function getDownloadFilename(response) {
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    if (match !== null) {
        return match[1];
    }
    if (currentMode === "compress") {
        return "compressed.bin";
    }
    return "restored-file";
}

// Đọc thông báo HTTP lỗi. Không hiển thị nguyên trang HTML lỗi của server.
async function getErrorMessage(response) {
    let message = "Xử lý thất bại (HTTP " + response.status + "). Vui lòng thử lại.";
    try {
        const body = await response.json();
        if (typeof body.detail === "string") {
            message = body.detail;
        }
    } catch (error) {
        // Một số lỗi mạng/server không có JSON; giữ thông báo mặc định ở trên.
    }
    return message;
}

// Hiển thị kết quả thật và tạo liên kết tải dữ liệu Blob về máy.
function showResult(response, resultBlob, elapsedSeconds) {
    const filename = getDownloadFilename(response);
    resultUrl = URL.createObjectURL(resultBlob);
    downloadLink.href = resultUrl;
    downloadLink.download = filename;
    document.getElementById("result-filename").textContent = filename;
    document.getElementById("input-size").textContent = formatSize(selectedFile.size);
    document.getElementById("output-size").textContent = formatSize(resultBlob.size);
    document.getElementById("elapsed-time").textContent = elapsedSeconds.toFixed(2) + " giây";

    const sizeChart = document.getElementById("size-chart");

    if (currentMode === "compress") {
        const ratio = Number(response.headers.get("X-Compression-Ratio"));
        document.getElementById("ratio-label").textContent = "Giảm dung lượng";
        document.getElementById("ratio-value").textContent = ratio.toFixed(2) + "%";
        if (ratio < 0) {
            document.getElementById("result-note").textContent = "File nén lớn hơn bản gốc vì dữ liệu và bảng tần suất. Đây không phải lỗi.";
        } else {
            document.getElementById("result-note").textContent = "File .bin chứa dữ liệu nén và thông tin để giải nén bằng ShrinkIT.";
        }

        // Vẽ biểu đồ so sánh dung lượng
        sizeChart.hidden = false;
        const originalSize = selectedFile.size;
        const compressedSize = resultBlob.size;
        const maxSize = Math.max(originalSize, compressedSize, 1);
        const originalPercent = Math.max(Math.round((originalSize / maxSize) * 100), 2);
        const compressedPercent = Math.max(Math.round((compressedSize / maxSize) * 100), 2);

        document.getElementById("chart-original-size").textContent = formatSize(originalSize);
        document.getElementById("chart-compressed-size").textContent = formatSize(compressedSize);

        const savingBadge = document.getElementById("chart-saving-badge");
        if (savingBadge) {
            if (ratio > 0) {
                savingBadge.textContent = "Giảm " + ratio.toFixed(1) + "%";
                savingBadge.className = "badge-saving saving-good";
                savingBadge.hidden = false;
            } else if (ratio < 0) {
                savingBadge.textContent = "Tăng " + Math.abs(ratio).toFixed(1) + "%";
                savingBadge.className = "badge-saving saving-warn";
                savingBadge.hidden = false;
            } else {
                savingBadge.hidden = true;
            }
        }

        // Delay một nhịp để transition CSS kích hoạt mượt mà
        setTimeout(function () {
            var oFill = document.getElementById("original-bar-fill");
            var cFill = document.getElementById("compressed-bar-fill");
            if (oFill) { oFill.style.width = originalPercent + "%"; }
            if (cFill) { cFill.style.width = compressedPercent + "%"; }
        }, 60);
    } else {
        sizeChart.hidden = true;
        document.getElementById("ratio-label").textContent = "Trạng thái";
        document.getElementById("ratio-value").textContent = "Đã giải nén";
        document.getElementById("result-note").textContent = "Dữ liệu đã được khôi phục. Tải file kết quả về máy của bạn.";
    }
    document.getElementById("empty-result").hidden = true;
    document.getElementById("result-content").hidden = false;
}

// Gửi file bằng multipart/form-data. await chờ phản hồi mà không khóa trang.
async function submitFile(event) {
    event.preventDefault();
    if (selectedFile === null || isProcessing || configuration === null) {
        return;
    }
    clearResult();
    isProcessing = true;
    updateControls();
    showStatus("Đang gửi và xử lý file. Vui lòng chờ…");
    const startTime = performance.now();
    const formData = new FormData();
    formData.append("file", selectedFile);
    let endpoint = "/api/compress";
    if (currentMode === "decompress") {
        endpoint = "/api/decompress";
    }

    try {
        const response = await fetch(endpoint, { method: "POST", body: formData });
        if (!response.ok) {
            const message = await getErrorMessage(response);
            throw new Error(message);
        }
        const resultBlob = await response.blob();
        const elapsedSeconds = (performance.now() - startTime) / 1000;
        showResult(response, resultBlob, elapsedSeconds);
        showStatus("Hoàn tất. Bạn có thể tải file kết quả.");
    } catch (error) {
        if (error instanceof TypeError) {
            showStatus("Mất kết nối đến server. Kiểm tra kết nối rồi thử lại.", true);
        } else {
            showStatus(error.message, true);
        }
    } finally {
        isProcessing = false;
        updateControls();
    }
}

// Nhận file từ hộp thoại hệ điều hành.
function handleFileChange() {
    selectFile(fileInput.files[0]);
}

// Ngăn trình duyệt mở file khi kéo vào vùng upload.
function handleDragOver(event) {
    event.preventDefault();
    if (!isProcessing) {
        dropZone.classList.add("dragging");
    }
}

// Bỏ màu nhấn khi con trỏ rời vùng upload.
function handleDragLeave() {
    dropZone.classList.remove("dragging");
}

// Mỗi lần chỉ nhận một file, tránh âm thầm bỏ qua file người dùng chọn.
function handleDrop(event) {
    event.preventDefault();
    handleDragLeave();
    if (isProcessing || configuration === null) {
        return;
    }
    if (event.dataTransfer.files.length !== 1) {
        clearSelection();
        showStatus("Mỗi lần chỉ xử lý một file.", true);
        return;
    }
    selectFile(event.dataTransfer.files[0]);
}

// Chuyển giao diện sang chế độ nén khi nhấn nút Nén file.
function chooseCompressMode() {
    changeMode("compress");
}

// Chuyển giao diện sang chế độ khôi phục file khi nhấn nút Giải nén.
function chooseDecompressMode() {
    changeMode("decompress");
}

// Bỏ file đã chọn và đưa trang về trạng thái chờ chọn file.
function removeSelectedFile() {
    clearSelection();
    showStatus("Chọn một file để bắt đầu.");
}

compressButton.addEventListener("click", chooseCompressMode);
decompressButton.addEventListener("click", chooseDecompressMode);
fileInput.addEventListener("change", handleFileChange);
removeButton.addEventListener("click", removeSelectedFile);
dropZone.addEventListener("dragover", handleDragOver);
dropZone.addEventListener("dragleave", handleDragLeave);
dropZone.addEventListener("drop", handleDrop);
document.getElementById("file-form").addEventListener("submit", submitFile);
window.addEventListener("pagehide", clearResult);
loadConfiguration();
