'use strict';
// 渐进增强：没有 JS 时，SVG 和表格都可读，按钮保持隐藏。
(function () {
  function activate(card, selected) {
    var buttons = card.querySelectorAll('[role="tab"]');
    for (var i = 0; i < buttons.length; i += 1) {
      var button = buttons[i];
      var active = button === selected;
      button.setAttribute('aria-selected', active ? 'true' : 'false');
      button.tabIndex = active ? 0 : -1;
      document.getElementById(button.getAttribute('aria-controls')).hidden = !active;
    }
  }
  function onClick(event) {
    var button = event.target.closest('[role="tab"]');
    if (!button) return;
    activate(button.closest('.chart-card'), button);
  }
  function onKey(event) {
    var button = event.target.closest('[role="tab"]');
    if (!button) return;
    var key = event.key;
    if (key !== 'ArrowLeft' && key !== 'ArrowRight' && key !== 'Home' && key !== 'End') return;
    event.preventDefault();
    var card = button.closest('.chart-card');
    var buttons = card.querySelectorAll('[role="tab"]');
    var next = buttons[0];
    if (key === 'End') next = buttons[buttons.length - 1];
    if (key === 'ArrowLeft' || key === 'ArrowRight') {
      next = button === buttons[0] ? buttons[1] : buttons[0];
    }
    activate(card, next);
    next.focus();
  }
  function onAnchorClick(event) {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (!event.target || typeof event.target.closest !== 'function') return;
    var link = event.target.closest('a[href^="#"]');
    if (!link || link.hasAttribute('download')) return;
    var targetWindow = link.getAttribute('target');
    if (targetWindow && targetWindow !== '_self') return;
    var hash = link.getAttribute('href');
    if (!/^#[A-Za-z0-9-]+$/.test(hash)) return;
    var target = document.getElementById(hash.slice(1));
    if (!target || typeof window.scrollTo !== 'function') return;
    // 成功手动滚动才拦截默认行为；失败时保留原生锚点回退。
    try {
      var offset = window.pageYOffset || document.documentElement.scrollTop || 0;
      var top = target.getBoundingClientRect().top + offset - 20;
      window.scrollTo(0, Math.max(0, top));
    } catch (error) {
      return;
    }
    event.preventDefault();
    // 部分离线 WebView 禁止修改历史；这不能影响目录滚动或图表切换。
    try {
      window.history.replaceState(null, '', hash);
    } catch (error) {
      // 保留滚动结果，不依赖 hash 修改成功。
    }
  }
  document.addEventListener('click', onAnchorClick);
  var cards = document.querySelectorAll('.chart-card');
  for (var i = 0; i < cards.length; i += 1) {
    var card = cards[i];
    var tabs = card.querySelector('.chart-tabs');
    tabs.addEventListener('click', onClick);
    tabs.addEventListener('keydown', onKey);
    tabs.hidden = false;
    activate(card, tabs.querySelector('[role="tab"]'));
  }
}());
