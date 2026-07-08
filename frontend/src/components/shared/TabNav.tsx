'use client';

type TabNavProps = {
  tabs: string[];
  active: string;
  onChange: (tab: string) => void;
};

export function TabNav({ tabs, active, onChange }: TabNavProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onChange(tab)}
          className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
            active === tab ? 'bg-[#2563EB] text-white' : 'bg-white text-slate-500 ring-1 ring-slate-200 hover:text-slate-900'
          }`}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}

