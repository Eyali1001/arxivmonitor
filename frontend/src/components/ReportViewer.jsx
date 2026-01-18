import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getReports, getReport } from '../api';

export default function ReportViewer() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportContent, setReportContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch available reports on mount
  useEffect(() => {
    async function fetchReports() {
      try {
        const data = await getReports();
        setReports(data);
        setLoading(false);
      } catch (err) {
        setError('Failed to load reports list');
        setLoading(false);
      }
    }
    fetchReports();
  }, []);

  // Fetch report content when selected
  useEffect(() => {
    if (!selectedReport) {
      setReportContent(null);
      return;
    }

    async function fetchContent() {
      setLoading(true);
      try {
        const data = await getReport(selectedReport);
        setReportContent(data);
        setError(null);
      } catch (err) {
        setError('Failed to load report');
      } finally {
        setLoading(false);
      }
    }
    fetchContent();
  }, [selectedReport]);

  if (error && !reportContent) {
    return <div className="report-viewer error">{error}</div>;
  }

  return (
    <div className="report-viewer">
      <div className="report-header">
        <h2>Analysis Reports</h2>
        <select
          value={selectedReport || ''}
          onChange={(e) => setSelectedReport(e.target.value || null)}
          style={{
            padding: '8px 12px',
            borderRadius: '6px',
            border: '1px solid #d1d5db',
            fontSize: '14px',
            minWidth: '200px'
          }}
        >
          <option value="">Select a report...</option>
          {reports.map((report) => (
            <option key={report.id} value={report.id}>
              {report.name}
            </option>
          ))}
        </select>
      </div>

      {loading && selectedReport && (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6b7280' }}>
          Loading report...
        </div>
      )}

      {!selectedReport && !loading && (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6b7280' }}>
          <p>Select a category to view its detailed analysis report.</p>
          <p style={{ fontSize: '13px', marginTop: '10px' }}>
            Reports include growth trends, market share analysis, correlations, and more.
          </p>
        </div>
      )}

      {reportContent && !loading && (
        <div className="report-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({ node, ...props }) => (
                <div style={{ overflowX: 'auto' }}>
                  <table {...props} />
                </div>
              ),
              h1: ({ node, ...props }) => (
                <h1 style={{ borderBottom: '2px solid #e5e7eb', paddingBottom: '10px' }} {...props} />
              ),
              h2: ({ node, ...props }) => (
                <h2 style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '8px', marginTop: '30px' }} {...props} />
              ),
              hr: () => (
                <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '20px 0' }} />
              ),
            }}
          >
            {reportContent.content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}
