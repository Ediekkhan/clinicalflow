export function PatientSettings() {
  return (
    <section className="grid gap-4 xl:grid-cols-2">
      <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-slate-900">Personal profile</h3>
        <div className="mt-5 grid gap-4">
          {['Full name', 'Phone number', 'Emergency contact', 'HMO provider'].map((label, index) => (
            <label key={label} className="grid gap-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</span>
              <input className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100" defaultValue={index === 0 ? 'Adaeze Chukwu' : ''} placeholder={label} />
            </label>
          ))}
        </div>
      </article>
      <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-slate-900">Health information</h3>
        <div className="mt-5 grid gap-4">
          {['Blood group', 'Genotype', 'Known allergies', 'Current medications'].map((label) => (
            <label key={label} className="grid gap-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</span>
              <input className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100" placeholder={label} />
            </label>
          ))}
        </div>
      </article>
    </section>
  );
}
