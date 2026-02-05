"""Observability HTML 渲染器

生成双栏静态 HTML 页面，用于可视化分析结果。
"""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diting.models.observability import ObservabilityData, ObservabilityTopic


class ObservabilityHtmlRenderer:
    """渲染 observability HTML 页面"""

    def render(self, data: ObservabilityData) -> str:
        """渲染完整的 HTML 页面

        Args:
            data: Observability 数据

        Returns:
            HTML 字符串
        """
        chatroom_name = html.escape(data.chatroom_name or data.chatroom_id)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>消息分析 Observability - {chatroom_name}</title>
    <style>{self._get_styles()}</style>
</head>
<body>
    <header class="header">
        <h1>📊 消息分析 Observability</h1>
        <div class="meta">
            <span>群聊: {chatroom_name}</span>
            <span>日期: {html.escape(data.date_range)}</span>
            <span>消息数: {data.total_messages}</span>
            <span>批次数: {data.batch_count}</span>
            <span>话题数: {len(data.topics)}</span>
        </div>
    </header>
    <div class="container">
        <div class="left-panel">
            <h2>话题列表</h2>
            <div class="topic-list">
                {self._render_topic_list(data.topics)}
            </div>
        </div>
        <div class="right-panel">
            <h2>消息详情</h2>
            <div id="message-detail">
                <p class="hint">← 点击左侧话题查看消息</p>
            </div>
        </div>
    </div>
    {self._render_topic_data_script(data)}
    <script>{self._get_script()}</script>
</body>
</html>"""

    def render_multi(self, data_list: list[ObservabilityData]) -> str:
        """渲染多个群聊的 HTML 页面

        Args:
            data_list: Observability 数据列表

        Returns:
            HTML 字符串
        """
        if not data_list:
            return self._render_empty_page()
        if len(data_list) == 1:
            return self.render(data_list[0])

        # 多群聊合并渲染
        total_messages = sum(d.total_messages for d in data_list)
        total_topics = sum(len(d.topics) for d in data_list)
        chatroom_names = ", ".join(html.escape(d.chatroom_name or d.chatroom_id) for d in data_list)

        # 合并所有话题，添加群聊前缀
        all_topics_html = []
        for data in data_list:
            chatroom_label = html.escape(data.chatroom_name or data.chatroom_id)
            all_topics_html.append('<div class="chatroom-section">')
            all_topics_html.append(f'<h3 class="chatroom-label">📱 {chatroom_label}</h3>')
            all_topics_html.append(self._render_topic_list(data.topics, data.chatroom_id))
            all_topics_html.append("</div>")

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>消息分析 Observability - 多群聊</title>
    <style>{self._get_styles()}</style>
</head>
<body>
    <header class="header">
        <h1>📊 消息分析 Observability</h1>
        <div class="meta">
            <span>群聊: {chatroom_names}</span>
            <span>总消息数: {total_messages}</span>
            <span>总话题数: {total_topics}</span>
        </div>
    </header>
    <div class="container">
        <div class="left-panel">
            <h2>话题列表</h2>
            <div class="topic-list">
                {"".join(all_topics_html)}
            </div>
        </div>
        <div class="right-panel">
            <h2>消息详情</h2>
            <div id="message-detail">
                <p class="hint">← 点击左侧话题查看消息</p>
            </div>
        </div>
    </div>
    {self._render_multi_topic_data_script(data_list)}
    <script>{self._get_script()}</script>
</body>
</html>"""

    def _render_empty_page(self) -> str:
        """渲染空页面"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>消息分析 Observability</title>
</head>
<body>
    <h1>无数据</h1>
    <p>没有可显示的分析结果。</p>
</body>
</html>"""

    def _render_topic_list(self, topics: list[ObservabilityTopic], chatroom_id: str = "") -> str:
        """渲染话题列表

        Args:
            topics: 话题列表
            chatroom_id: 群聊 ID（用于多群聊区分）

        Returns:
            HTML 字符串
        """
        if not topics:
            return '<p class="no-topics">无话题</p>'

        items = []
        for topic in topics:
            topic_key = (
                f"{chatroom_id}_{topic.topic_index}" if chatroom_id else str(topic.topic_index)
            )
            keywords_html = " ".join(
                f'<span class="tag">{html.escape(kw)}</span>' for kw in topic.keywords[:5]
            )
            escaped_key = html.escape(topic_key)
            items.append(
                f"""
            <div class="topic-card" data-topic-key="{escaped_key}"
                 onclick="showTopic('{escaped_key}')">
                <div class="topic-header">
                    <span class="topic-index">#{topic.topic_index}</span>
                    <span class="topic-category">{html.escape(topic.category)}</span>
                </div>
                <h3 class="topic-title">{html.escape(topic.title)}</h3>
                <div class="topic-meta">
                    <span>💬 {topic.message_count}</span>
                    <span>👥 {len(topic.participants)}</span>
                    <span>🕒 {html.escape(topic.time_range)}</span>
                </div>
                <p class="topic-summary">{html.escape(topic.summary)}</p>
                <p class="topic-notes"><em>{html.escape(topic.notes)}</em></p>
                <div class="topic-tags">{keywords_html}</div>
            </div>
            """
            )
        return "\n".join(items)

    def _render_topic_data_script(self, data: ObservabilityData) -> str:
        """将话题数据嵌入为 JSON

        Args:
            data: Observability 数据

        Returns:
            script 标签字符串
        """
        # 构建话题数据映射
        topics_data = {}
        for topic in data.topics:
            topic_key = str(topic.topic_index)
            topics_data[topic_key] = {
                "title": topic.title,
                "messages": [
                    {
                        "seq_id": msg.seq_id,
                        "time_str": msg.time_str,
                        "sender": msg.sender,
                        "display_content": msg.display_content,
                        "message_type": msg.message_type.value,
                        "batch_index": msg.batch_index,
                        "refers_to_seq_id": msg.refers_to_seq_id,
                        "ocr_content": msg.ocr_content,
                        "image_url": msg.image_url,
                        "share_url": msg.share_url,
                    }
                    for msg in topic.messages
                ],
            }

        json_data = json.dumps(topics_data, ensure_ascii=False)
        return f"<script>const TOPICS_DATA = {json_data};</script>"

    def _render_multi_topic_data_script(self, data_list: list[ObservabilityData]) -> str:
        """将多群聊话题数据嵌入为 JSON

        Args:
            data_list: Observability 数据列表

        Returns:
            script 标签字符串
        """
        topics_data = {}
        for data in data_list:
            for topic in data.topics:
                topic_key = f"{data.chatroom_id}_{topic.topic_index}"
                topics_data[topic_key] = {
                    "title": topic.title,
                    "chatroom_id": data.chatroom_id,
                    "messages": [
                        {
                            "seq_id": msg.seq_id,
                            "time_str": msg.time_str,
                            "sender": msg.sender,
                            "display_content": msg.display_content,
                            "message_type": msg.message_type.value,
                            "batch_index": msg.batch_index,
                            "refers_to_seq_id": msg.refers_to_seq_id,
                            "ocr_content": msg.ocr_content,
                            "image_url": msg.image_url,
                            "share_url": msg.share_url,
                        }
                        for msg in topic.messages
                    ],
                }

        json_data = json.dumps(topics_data, ensure_ascii=False)
        return f"<script>const TOPICS_DATA = {json_data};</script>"

    def _get_styles(self) -> str:
        """CSS 样式"""
        # noqa: E501 - CSS styles contain long lines for readability
        return """
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
    background: #f5f5f5;
    color: #333;
    line-height: 1.6;
}

.header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    text-align: center;
}

.header h1 {
    font-size: 1.5rem;
    margin-bottom: 10px;
}

.header .meta {
    display: flex;
    justify-content: center;
    gap: 20px;
    flex-wrap: wrap;
    font-size: 0.9rem;
    opacity: 0.9;
}

.container {
    display: flex;
    height: calc(100vh - 100px);
}

.left-panel {
    width: 35%;
    min-width: 300px;
    background: white;
    border-right: 1px solid #e0e0e0;
    overflow-y: auto;
    padding: 15px;
}

.left-panel h2 {
    font-size: 1.1rem;
    color: #555;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 2px solid #667eea;
}

.right-panel {
    flex: 1;
    background: #fafafa;
    overflow-y: auto;
    padding: 15px;
}

.right-panel h2 {
    font-size: 1.1rem;
    color: #555;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 2px solid #764ba2;
}

.topic-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.chatroom-section {
    margin-bottom: 20px;
}

.chatroom-label {
    font-size: 1rem;
    color: #667eea;
    margin-bottom: 10px;
    padding: 8px;
    background: #f0f0ff;
    border-radius: 6px;
}

.topic-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.topic-card:hover {
    border-color: #667eea;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

.topic-card.active {
    border-color: #667eea;
    background: #f8f9ff;
    box-shadow: 0 2px 12px rgba(102, 126, 234, 0.3);
}

.topic-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.topic-index {
    font-size: 0.8rem;
    color: #888;
    font-weight: 600;
}

.topic-category {
    font-size: 0.75rem;
    background: #667eea;
    color: white;
    padding: 2px 8px;
    border-radius: 10px;
}

.topic-title {
    font-size: 1rem;
    color: #333;
    margin-bottom: 8px;
}

.topic-meta {
    display: flex;
    gap: 12px;
    font-size: 0.8rem;
    color: #666;
    margin-bottom: 8px;
}

.topic-summary {
    font-size: 0.85rem;
    color: #555;
    margin-bottom: 6px;
}

.topic-notes {
    font-size: 0.8rem;
    color: #888;
    margin-bottom: 8px;
}

.topic-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.tag {
    font-size: 0.7rem;
    background: #e8e8e8;
    color: #666;
    padding: 2px 8px;
    border-radius: 10px;
}

.hint {
    color: #999;
    text-align: center;
    padding: 40px;
    font-size: 1rem;
}

.no-topics {
    color: #999;
    text-align: center;
    padding: 20px;
}

/* 消息详情样式 */
.message-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.chunk-group {
    background: white;
    border: 1px dashed #ccc;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 12px;
}

.chunk-header {
    font-size: 0.8rem;
    color: #888;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #eee;
}

.message-item {
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.85rem;
    margin-bottom: 4px;
    position: relative;
}

.message-item.text {
    background: #fff;
    border-left: 3px solid #4caf50;
}

.message-item.image {
    background: #e3f2fd;
    border-left: 3px solid #2196f3;
}

.message-item.quote {
    background: #fff3e0;
    border-left: 3px solid #ff9800;
}

.message-item.share {
    background: #e8f5e9;
    border-left: 3px solid #8bc34a;
}

.message-item.filtered {
    background: #f5f5f5;
    border-left: 3px solid #9e9e9e;
    color: #999;
    font-style: italic;
}

.message-seq {
    font-weight: 600;
    color: #667eea;
    margin-right: 8px;
}

.message-time {
    color: #888;
    font-size: 0.75rem;
    margin-right: 8px;
}

.message-sender {
    color: #333;
    font-weight: 500;
    margin-right: 8px;
}

.message-content {
    color: #555;
}

.message-type-icon {
    position: absolute;
    right: 8px;
    top: 8px;
    font-size: 0.9rem;
}

.reference-link {
    display: inline-block;
    margin-left: 8px;
    font-size: 0.75rem;
    color: #667eea;
    cursor: pointer;
    text-decoration: underline;
}

.reference-link:hover {
    color: #764ba2;
}

.share-link {
    display: inline-block;
    margin-left: 8px;
    font-size: 0.75rem;
    color: #4caf50;
    text-decoration: none;
}

.share-link:hover {
    color: #2e7d32;
    text-decoration: underline;
}

.ocr-content {
    margin-top: 6px;
    padding: 6px 10px;
    background: #f0f7ff;
    border-radius: 4px;
    font-size: 0.8rem;
    color: #1565c0;
    border-left: 2px solid #2196f3;
}

.highlight {
    animation: highlight-pulse 1s ease-out;
}

@keyframes highlight-pulse {
    0% { background-color: #ffeb3b; }
    100% { background-color: inherit; }
}

/* 图片预览样式 */
.image-preview-trigger {
    cursor: pointer;
    position: relative;
    display: inline-block;
}

.image-preview-container {
    position: fixed;
    pointer-events: none;
    z-index: 1000;
    opacity: 0;
    transform: translateX(20px);
    transition: opacity 0.2s ease, transform 0.2s ease;
}

.image-preview-container.visible {
    opacity: 1;
    transform: translateX(0);
}

.image-preview-container img {
    max-width: 300px;
    max-height: 300px;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    background: white;
}

/* 响应式 */
@media (max-width: 768px) {
    .container {
        flex-direction: column;
        height: auto;
    }
    .left-panel {
        width: 100%;
        min-width: auto;
        max-height: 40vh;
    }
    .right-panel {
        min-height: 60vh;
    }
}
"""

    def _get_script(self) -> str:
        """JavaScript 交互逻辑"""
        return """
let currentTopicKey = null;

function showTopic(topicKey) {
    // 更新选中状态
    document.querySelectorAll('.topic-card').forEach(card => {
        card.classList.remove('active');
    });
    const activeCard = document.querySelector(`[data-topic-key="${topicKey}"]`);
    if (activeCard) {
        activeCard.classList.add('active');
    }

    currentTopicKey = topicKey;
    const topic = TOPICS_DATA[topicKey];
    if (!topic) {
        document.getElementById('message-detail').innerHTML = '<p class="hint">话题数据未找到</p>';
        return;
    }

    // 按 batch_index 分组
    const chunks = {};
    topic.messages.forEach(msg => {
        const batchIndex = msg.batch_index;
        if (!chunks[batchIndex]) {
            chunks[batchIndex] = [];
        }
        chunks[batchIndex].push(msg);
    });

    // 渲染消息
    let html = `<div class="message-container">`;

    const sortedBatchIndices = Object.keys(chunks)
        .map(Number).sort((a, b) => a - b);
    sortedBatchIndices.forEach(batchIndex => {
        const messages = chunks[batchIndex];
        html += `<div class="chunk-group">`;
        html += `<div class="chunk-header">` +
            `📦 Chunk ${batchIndex} (${messages.length} 条消息)</div>`;

        messages.forEach(msg => {
            const typeIcon = getTypeIcon(msg.message_type, msg.image_url);
            const refLink = msg.refers_to_seq_id
                ? `<span class="reference-link" ` +
                  `onclick="scrollToMessage(${msg.refers_to_seq_id})">` +
                  `→ 引用 #${msg.refers_to_seq_id}</span>`
                : '';

            // 移除显示内容中的前缀 (seq_id, timestamp, sender)
            const prefixRe = new RegExp(
                '^\\\\[\\\\d+\\\\]\\\\s*\\\\d{4}-\\\\d{2}-\\\\d{2}\\\\s*' +
                '\\\\d{2}:\\\\d{2}:\\\\d{2}\\\\s*[^:]+:\\\\s*'
            );
            let content = msg.display_content.replace(prefixRe, '');

            // 文章分享添加链接
            let shareLink = '';
            if (msg.message_type === 'share' && msg.share_url) {
                shareLink = `<a href="${escapeHtml(msg.share_url)}" ` +
                    `target="_blank" class="share-link">🔗 原文</a>`;
            }

            // 图片 OCR 内容
            let ocrBlock = '';
            if (msg.message_type === 'image' && msg.ocr_content) {
                ocrBlock = `<div class="ocr-content">` +
                    `📝 OCR: ${escapeHtml(msg.ocr_content)}</div>`;
            }

            html += `
                <div class="message-item ${msg.message_type}" id="msg-${msg.seq_id}">
                    <span class="message-type-icon">${typeIcon}</span>
                    <span class="message-seq">#${msg.seq_id}</span>
                    <span class="message-time">${escapeHtml(msg.time_str)}</span>
                    <span class="message-sender">${escapeHtml(msg.sender)}:</span>
                    <span class="message-content">${escapeHtml(content)}</span>
                    ${shareLink}
                    ${refLink}
                    ${ocrBlock}
                </div>
            `;
        });

        html += `</div>`;
    });

    html += `</div>`;
    document.getElementById('message-detail').innerHTML = html;
}

function getTypeIcon(type, imageUrl) {
    const icons = {
        'text': '',
        'image': '🖼️',
        'quote': '💬',
        'share': '📄',
        'filtered': '⊘'
    };
    const icon = icons[type] || '';
    // 图片类型且有 URL 时，添加预览触发器
    if (type === 'image' && imageUrl) {
        return `<span class="image-preview-trigger" ` +
            `data-image-url="${escapeHtml(imageUrl)}">${icon}</span>`;
    }
    return icon;
}

function scrollToMessage(seqId) {
    const element = document.getElementById(`msg-${seqId}`);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        element.classList.add('highlight');
        setTimeout(() => element.classList.remove('highlight'), 1000);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 图片预览容器（全局单例）
let imagePreviewContainer = null;

function initImagePreview() {
    // 创建预览容器
    imagePreviewContainer = document.createElement('div');
    imagePreviewContainer.className = 'image-preview-container';
    imagePreviewContainer.innerHTML = '<img src="" alt="预览">';
    document.body.appendChild(imagePreviewContainer);
}

// 图片预览的鼠标事件处理
function setupImagePreviewEvents() {
    const previewImg = imagePreviewContainer.querySelector('img');

    // 使用事件委托，因为消息是动态渲染的
    document.addEventListener('mouseover', function(event) {
        const trigger = event.target.closest('.image-preview-trigger');
        if (!trigger) return;

        const imageUrl = trigger.dataset.imageUrl;
        if (!imageUrl) return;

        // 设置图片 URL
        previewImg.src = imageUrl;

        // 计算预览位置（显示在鼠标左侧）
        const previewWidth = 320; // 预览容器宽度 + padding
        const gap = 15; // 与鼠标的间距

        let left = event.clientX - previewWidth - gap;
        let top = event.clientY - 50;

        // 边界检查：如果左侧空间不足，显示在右侧
        if (left < 10) {
            left = event.clientX + gap;
        }

        // 边界检查：确保不超出视口底部
        const viewportHeight = window.innerHeight;
        if (top + 320 > viewportHeight) {
            top = viewportHeight - 330;
        }
        if (top < 10) {
            top = 10;
        }

        imagePreviewContainer.style.left = left + 'px';
        imagePreviewContainer.style.top = top + 'px';

        // 显示预览（触发滑动动画）
        imagePreviewContainer.classList.add('visible');
    });

    document.addEventListener('mouseout', function(event) {
        const trigger = event.target.closest('.image-preview-trigger');
        if (!trigger) return;

        // 检查是否移动到了预览容器内（不应该隐藏）
        const relatedTarget = event.relatedTarget;
        if (relatedTarget && imagePreviewContainer.contains(relatedTarget)) {
            return;
        }

        // 隐藏预览
        imagePreviewContainer.classList.remove('visible');
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initImagePreview();
    setupImagePreviewEvents();
});
"""
