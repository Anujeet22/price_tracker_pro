document.addEventListener("DOMContentLoaded", function () {

  // Scroll Progress Bar
  var progressBar = document.getElementById("scrollProgress");
  if (progressBar) {
    window.addEventListener("scroll", function () {
      var scrolled = window.scrollY;
      var height = document.documentElement.scrollHeight - window.innerHeight;
      progressBar.style.width = (height > 0 ? (scrolled / height) * 100 : 0) + "%";
    }, { passive: true });
  }

  // Scroll Reveal
  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("active");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -50px 0px" });
    document.querySelectorAll(".reveal").forEach(function (el) { observer.observe(el); });
  } else {
    document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("active"); });
  }

  // Search Clear Button
  var urlInput = document.getElementById("product-url");
  var clearBtn = document.getElementById("clear-search-btn");
  if (urlInput && clearBtn) {
    urlInput.addEventListener("input", function () {
      clearBtn.style.display = this.value.trim() ? "flex" : "none";
    });
    clearBtn.addEventListener("click", function () {
      urlInput.value = "";
      clearBtn.style.display = "none";
      urlInput.focus();
    });
  }

  // Track Button Loading Animation
  var trackBtn = document.getElementById("track-btn");
  if (trackBtn) {
    trackBtn.addEventListener("click", function () {
      var input = document.getElementById("product-url");
      if (!input || !input.value.trim()) return;

      var btnIcon = this.querySelector(".btn-icon");
      var btnText = this.querySelector(".btn-text");
      this.disabled = true;
      btnIcon.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="animation:spin 1s linear infinite;width:100%;height:100%;"><circle cx="12" cy="12" r="10" stroke-width="2" fill="none" opacity="0.25"></circle><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" opacity="0.75"></path></svg>';
      btnText.textContent = "Tracking...";

      // show the spinner briefly then submit the form for real
      var form = this.closest("form");
      if (form) {
        setTimeout(function () { form.submit(); }, 600);
      }
    });
  }

  // Tab Navigation
  var navTabs = document.querySelectorAll(".nav-tab");
  navTabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      var tabName = this.getAttribute("data-tab");
      navTabs.forEach(function (t) { t.classList.remove("active"); });
      this.classList.add("active");
      document.querySelectorAll(".tab-section").forEach(function (s) { s.style.display = "none"; });
      var selected = document.getElementById("section-" + tabName);
      if (selected) {
        selected.style.display = "block";
        window.scrollTo({ top: 0, behavior: "smooth" });
        selected.querySelectorAll(".reveal").forEach(function (el) {
          el.classList.remove("active");
          setTimeout(function () { el.classList.add("active"); }, 50);
        });
      }
    });
  });

  // Toggle Switches
  document.querySelectorAll(".toggle").forEach(function (toggle) {
    toggle.addEventListener("click", function (e) {
      e.preventDefault();
      this.classList.toggle("active");
    });
  });
});

// ── Price History Tab ────────────────────────────────────────────────────────

function loadHistory(productId) {
  // Show loading, hide cards
  document.getElementById('history-loading').style.display = 'block';
  document.getElementById('history-chart-card').style.display = 'none';
  document.getElementById('history-table-card').style.display = 'none';
  document.getElementById('history-record-count').style.display = 'none';

  fetch('/api/history/' + productId)
    .then(function(res) { return res.json(); })
    .then(function(data) {
      document.getElementById('history-loading').style.display = 'none';
      renderHistory(data);
    })
    .catch(function(err) {
      document.getElementById('history-loading').style.display = 'none';
      console.error('History load failed:', err);
    });
}

function renderHistory(data) {
  var records  = data.records;
  var currency = data.currency;

  // ── Header ────────────────────────────────────────────────────────────────
  document.getElementById('history-product-name').textContent = data.name;
  document.getElementById('history-current-price').textContent =
    currency + ' ' + parseFloat(data.current_price).toFixed(2);

  // Show "All-time Low" badge if current == lowest
  var lowBadge = document.getElementById('history-low-badge');
  if (data.current_price && data.lowest_price &&
      parseFloat(data.current_price) <= parseFloat(data.lowest_price)) {
    lowBadge.style.display = 'inline-flex';
  } else {
    lowBadge.style.display = 'none';
  }

  // Show record count badge
  var countBadge = document.getElementById('history-record-count');
  document.getElementById('history-record-text').textContent =
    records.length + ' record' + (records.length !== 1 ? 's' : '');
  countBadge.style.display = 'inline-flex';

  // Show chart card
  document.getElementById('history-chart-card').style.display = 'block';

  // ── Chart ─────────────────────────────────────────────────────────────────
  // ── Chart ─────────────────────────────────────────────────────────────────
  var chartContainer = document.getElementById('history-chart-container');
  var noChart        = document.getElementById('history-no-chart');
  var statsRow       = document.getElementById('history-stats-row');
  var cd             = data.chart_data;

  // Destroy previous chart instance if it exists
  if (window._historyChart) {
    window._historyChart.destroy();
    window._historyChart = null;
  }

  if (cd && cd.prices && cd.prices.length >= 2) {
    chartContainer.style.display = 'block';
    noChart.style.display        = 'none';

    // ── Stat boxes ───────────────────────────────────────────────────────────
    statsRow.style.display = 'grid';
    document.getElementById('stat-avg').textContent =
      currency + ' ' + cd.avg_price.toFixed(2);
    document.getElementById('stat-lowest').textContent =
      currency + ' ' + parseFloat(data.lowest_price).toFixed(2);
    document.getElementById('stat-highest').textContent =
      currency + ' ' + parseFloat(data.highest_price).toFixed(2);
    document.getElementById('stat-volatility').textContent =
      currency + ' ' + cd.volatility.toFixed(2);

    var trendEl    = document.getElementById('stat-trend');
    var trendEmoji = cd.trend === 'rising' ? '↑ Rising' :
                     cd.trend === 'falling' ? '↓ Falling' : '→ Stable';
    var trendColor = cd.trend === 'rising'  ? 'var(--danger)' :
                     cd.trend === 'falling' ? 'var(--success)' : 'var(--text-tertiary)';
    trendEl.textContent   = trendEmoji;
    trendEl.style.color   = trendColor;

    // ── Chart.js ──────────────────────────────────────────────────────────────
    var ctx = document.getElementById('history-chart-canvas').getContext('2d');

    window._historyChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels:   cd.labels,
        datasets: [
          {
            // Actual price line
            label:           'Price',
            data:            cd.prices,
            borderColor:     '#0969da',
            backgroundColor: 'rgba(9, 105, 218, 0.08)',
            borderWidth:     2.5,
            pointRadius:     4,
            pointHoverRadius: 7,
            pointBackgroundColor: '#0969da',
            pointBorderColor:     '#ffffff',
            pointBorderWidth:     2,
            fill:            true,
            tension:         0.4,
          },
          {
            // Moving average line — pandas calculated
            label:           'Moving Avg',
            data:            cd.moving_avg,
            borderColor:     'rgba(255, 165, 0, 0.8)',
            borderWidth:     1.5,
            borderDash:      [6, 3],
            pointRadius:     0,
            fill:            false,
            tension:         0.4,
          }
        ]
      },
      options: {
        responsive:          true,
        maintainAspectRatio: false,
        interaction: {
          mode:      'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display:  true,
            position: 'top',
            labels: {
              usePointStyle: true,
              pointStyleWidth: 8,
              font: { size: 12, family: 'Inter, sans-serif' },
              color: '#57606a',
              padding: 16,
            }
          },
          tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.92)',
            titleColor:      '#e2e8f0',
            bodyColor:       '#94a3b8',
            borderColor:     'rgba(255,255,255,0.1)',
            borderWidth:     1,
            padding:         12,
            cornerRadius:    10,
            callbacks: {
              label: function(ctx) {
                var val = ctx.parsed.y.toFixed(2);
                return '  ' + ctx.dataset.label + ':  ' + currency + ' ' + val;
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
            ticks: {
              font:  { size: 11, family: 'Inter, sans-serif' },
              color: '#768390',
              maxTicksLimit: 6,
            }
          },
          y: {
            position: 'right',
            grid: {
              color: 'rgba(0,0,0,0.04)',
            },
            ticks: {
              font:  { size: 11, family: 'Inter, sans-serif' },
              color: '#768390',
              callback: function(val) {
                return currency + ' ' + val.toFixed(0);
              }
            }
          }
        }
      }
    });

  } else {
    chartContainer.style.display = 'none';
    noChart.style.display        = 'block';
    statsRow.style.display       = 'none';
  }

  // ── Table ─────────────────────────────────────────────────────────────────
  var tbody = document.getElementById('history-table-body');
  tbody.innerHTML = '';

  // Show newest first
  var reversed = records.slice().reverse();

  reversed.forEach(function(record, idx) {
    var prevRecord = reversed[idx + 1];
    var changeHTML = '';

    if (prevRecord) {
      var diff = record.price - prevRecord.price;
      if (diff < 0) {
        changeHTML = '<span style="color:var(--success);font-weight:600;">↓ ' +
          currency + ' ' + Math.abs(diff).toFixed(2) + '</span>';
      } else if (diff > 0) {
        changeHTML = '<span style="color:var(--danger);font-weight:600;">↑ ' +
          currency + ' ' + diff.toFixed(2) + '</span>';
      } else {
        changeHTML = '<span style="color:var(--text-tertiary);">—</span>';
      }
    } else {
      changeHTML = '<span style="color:var(--text-tertiary);font-size:0.8125rem;">First record</span>';
    }

    var rowNum = records.length - idx;

    tbody.innerHTML += '<tr style="border-bottom:1px solid var(--border-subtle);">' +
      '<td style="padding:0.75rem 1.5rem;color:var(--text-tertiary);font-size:0.8125rem;">'
        + rowNum + '</td>' +
      '<td style="padding:0.75rem 1.5rem;color:var(--text-secondary);">'
        + record.checked_at + '</td>' +
      '<td style="padding:0.75rem 1.5rem;text-align:right;font-weight:600;color:var(--text);">'
        + currency + ' ' + parseFloat(record.price).toFixed(2) + '</td>' +
      '<td style="padding:0.75rem 1.5rem;text-align:right;">'
        + changeHTML + '</td>' +
    '</tr>';
  });

  document.getElementById('history-table-count').textContent =
    records.length + ' record' + (records.length !== 1 ? 's' : '');
  document.getElementById('history-table-card').style.display = 'block';
}

// ── Wire up dropdown + tab click ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
  var select = document.getElementById('history-product-select');
  if (!select) return;

  // Dropdown change → reload chart
  select.addEventListener('change', function() {
    loadHistory(this.value);
  });

  // When user clicks the History tab → auto load first product
  var historyTab = document.querySelector('.nav-tab[data-tab="history"]');
  if (historyTab) {
    historyTab.addEventListener('click', function() {
      if (select.value) loadHistory(select.value);
    });
  }
});