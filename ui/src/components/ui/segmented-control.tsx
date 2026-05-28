interface SegmentedControlProps {
  value: string;
  options: string[];
  onChange: (value: string) => void;
}

export function SegmentedControl({ value, options, onChange }: SegmentedControlProps) {
  return (
    <div className="segmented" role="listbox" aria-label="Segmented options">
      {options.map((option) => (
        <button key={option} type="button" className={option === value ? "active" : ""} onClick={() => onChange(option)}>
          {option}
        </button>
      ))}
    </div>
  );
}
