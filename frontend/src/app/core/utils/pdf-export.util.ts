export interface PdfExportOptions {
  title: string;
  subtitle?: string;
  filename?: string;
  metadata?: { label: string; value: string | number }[];
  headers: string[];
  rows: (string | number)[][];
  orientation?: 'portrait' | 'landscape';
}

function escapeHtml(value: string | number): string {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Generates an executive-styled, printable A4 PDF document and triggers the print/save-as-PDF dialog.
 */
export function exportTableToPdf(options: PdfExportOptions): void {
  const { title, subtitle, headers, rows, metadata } = options;
  const orientation = options.orientation || 'portrait';
  const nowStr = new Date().toLocaleString();

  const metadataHtml = metadata && metadata.length > 0
    ? `<div class="meta-grid">
        ${metadata.map(m => `
          <div class="meta-card">
            <span class="meta-label">${escapeHtml(m.label)}</span>
            <span class="meta-value">${escapeHtml(m.value)}</span>
          </div>
        `).join('')}
       </div>`
    : '';

  const tableHeaderHtml = headers.map(h => `<th>${escapeHtml(h)}</th>`).join('');
  const tableRowsHtml = rows.map((r, idx) => `
    <tr class="${idx % 2 === 0 ? 'even' : 'odd'}">
      ${r.map(cell => `<td>${escapeHtml(cell !== null && cell !== undefined ? cell : '-')}</td>`).join('')}
    </tr>
  `).join('');

  const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>${escapeHtml(title)}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    @page {
      size: A4 portrait;
      margin: 10mm 12mm;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      color: #0F172A;
      background: #FFFFFF;
      padding: 10px 14px;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }

    .report-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #2563EB;
      padding-bottom: 12px;
      margin-bottom: 14px;
    }

    .brand-title {
      font-size: 18px;
      font-weight: 800;
      color: #2563EB;
      letter-spacing: -0.5px;
      margin-bottom: 2px;
    }

    .doc-title {
      font-size: 14px;
      font-weight: 750;
      color: #0F172A;
      margin-bottom: 3px;
    }

    .doc-subtitle {
      font-size: 11px;
      color: #64748B;
      font-weight: 500;
    }

    .report-meta-right {
      text-align: right;
      font-size: 10.5px;
      color: #64748B;
      line-height: 1.5;
    }

    .meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
      gap: 8px;
      margin-bottom: 14px;
    }

    .meta-card {
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 6px 10px;
    }

    .meta-label {
      font-size: 9.5px;
      font-weight: 600;
      color: #64748B;
      text-transform: uppercase;
      display: block;
      margin-bottom: 2px;
    }

    .meta-value {
      font-size: 13px;
      font-weight: 750;
      color: #0F172A;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 9.5px;
      margin-top: 6px;
      table-layout: auto;
    }

    th {
      background-color: #1E3A8A !important;
      color: #FFFFFF !important;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.3px;
      padding: 6px 5px;
      text-align: center;
      border: 1px solid #CBD5E1;
      font-size: 8.5px;
      white-space: nowrap;
    }

    th:first-child, td:first-child {
      text-align: left;
    }

    td {
      padding: 6px 5px;
      border: 1px solid #E2E8F0;
      color: #1E293B;
      text-align: center;
      vertical-align: middle;
      font-size: 9.5px;
      white-space: nowrap;
    }

    tr.even td {
      background-color: #F8FAFC !important;
    }

    tr.odd td {
      background-color: #FFFFFF !important;
    }

    .footer {
      margin-top: 20px;
      padding-top: 10px;
      border-top: 1px solid #E2E8F0;
      display: flex;
      justify-content: space-between;
      font-size: 9px;
      color: #94A3B8;
    }

    @media print {
      body {
        padding: 0;
      }
      .no-print {
        display: none !important;
      }
    }
  </style>
</head>
<body>
  <div class="report-header">
    <div>
      <div class="brand-title">AIVAN 360 HR+</div>
      <div class="doc-title">${escapeHtml(title)}</div>
      ${subtitle ? `<div class="doc-subtitle">${escapeHtml(subtitle)}</div>` : ''}
    </div>
    <div class="report-meta-right">
      <div><strong>Generated On:</strong> ${nowStr}</div>
      <div><strong>Total Records:</strong> ${rows.length}</div>
      <div><strong>Status:</strong> Confidential / Official</div>
    </div>
  </div>

  ${metadataHtml}

  <table>
    <thead>
      <tr>${tableHeaderHtml}</tr>
    </thead>
    <tbody>
      ${tableRowsHtml}
    </tbody>
  </table>

  <div class="footer">
    <span>AIVAN 360 HR+ Enterprise Management System</span>
    <span>Generated by Authenticated User &bull; Page 1 of 1</span>
  </div>

  <script>
    window.onload = function() {
      setTimeout(function() {
        window.print();
      }, 300);
    };
  </script>
</body>
</html>
  `;

  const printWindow = window.open('', '_blank', 'width=1024,height=768');
  if (printWindow) {
    printWindow.document.open();
    printWindow.document.write(htmlContent);
    printWindow.document.close();
  } else {
    // Fallback if popup blocker active: write to hidden iframe and print
    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    document.body.appendChild(iframe);
    const doc = iframe.contentWindow?.document;
    if (doc) {
      doc.open();
      doc.write(htmlContent);
      doc.close();
      setTimeout(() => {
        iframe.contentWindow?.focus();
        iframe.contentWindow?.print();
        setTimeout(() => document.body.removeChild(iframe), 2000);
      }, 500);
    }
  }
}
