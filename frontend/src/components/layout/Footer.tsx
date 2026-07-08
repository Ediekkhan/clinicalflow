import Link from 'next/link';

const footerGroups = [
  { title: 'Platform', links: ['How It Works', 'For Patients', 'For Doctors', 'For Hospitals', 'For Pharmacies', 'For Laboratories', 'Pricing', 'Book a Demo'] },
  { title: 'Company', links: ['About Us', 'Blog', 'Careers', 'Press Kit', 'Partners', 'Contact Us'] },
  { title: 'Legal', links: ['Privacy Policy', 'Terms of Service', 'NDPA Compliance', 'Cookie Policy', 'Data Processing Agreement', 'Refund Policy'] },
];

const footerRoutes: Record<string, string> = {
  'How It Works': '/',
  'For Patients': '/signup?type=patient',
  'For Doctors': '/specialists',
  'For Hospitals': '/hospitals',
  'For Pharmacies': '/signup?type=pharmacy',
  'For Laboratories': '/signup?type=laboratory',
  Pricing: '/pricing',
  'Book a Demo': '/book-demo',
  'About Us': '/',
  Blog: '/blog',
  Careers: '/blog',
  'Press Kit': '/blog',
  Partners: '/book-demo',
  'Contact Us': '/book-demo',
  'Privacy Policy': '/privacy',
  'Terms of Service': '/terms',
  'NDPA Compliance': '/privacy#ndpa-compliance',
  'Cookie Policy': '/privacy#cookie-policy',
  'Data Processing Agreement': '/privacy#data-processing-agreement',
  'Refund Policy': '/terms#refund-policy',
};

export function Footer() {
  return (
    <footer className="bg-[#0D1117] px-6 pb-8 pt-16 text-slate-500">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 md:grid-cols-5">
          <div className="md:col-span-2">
            <Link href="/" className="font-display text-2xl text-white">SynaptiVerse</Link>
            <p className="mt-2 max-w-xs text-sm leading-6">AI-powered healthcare triage for Nigeria.</p>
            <div className="mt-6 space-y-2 text-xs text-slate-600">
              <p>hello@synaptiverse.ng</p>
              <p>+234 800 SYNAP TI</p>
              <p>Uyo, Akwa Ibom State, Nigeria</p>
            </div>
          </div>
          {footerGroups.map((group) => (
            <div key={group.title}>
              <h3 className="mb-4 text-sm font-semibold text-white">{group.title}</h3>
              <div className="grid gap-2.5">
                {group.links.map((link) => (
                  <Link key={link} href={footerRoutes[link] ?? '/'} className="text-sm transition hover:text-white">
                    {link} {link === 'Careers' ? <span className="ml-1 rounded border border-slate-800 px-1 text-[10px]">Soon</span> : null}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col gap-4 border-t border-slate-800 pt-8 text-xs text-slate-600 md:flex-row md:items-center md:justify-between">
          <p>© 2026 SynaptiVerse Health Technologies Ltd. Registered in Nigeria.</p>
          <p>Made with care in Akwa Ibom</p>
          <div className="flex gap-2">
            <span className="rounded border border-slate-800 px-2 py-1">NDPA 2023</span>
            <span className="rounded border border-slate-800 px-2 py-1">ISO 27001 In Progress</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
