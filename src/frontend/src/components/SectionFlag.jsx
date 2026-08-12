// Top-left section flag, e.g. "001 / DISCOVER". Numbered because the app really
// is a sequence of stations (onboard -> quiz -> discover -> connect).
export default function SectionFlag({ n, children }) {
  return (
    <div className="flag section-flag">
      <b>{String(n).padStart(3, '0')}</b> / {children}
    </div>
  );
}
