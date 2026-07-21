'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowRight, FileText, Star } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { api } from '@/lib/auth';

type BlogPost = { id?: string; title?: string; category?: string; excerpt?: string; published_at?: string };

const reviews = [
  {
    id: 'reliability-at-scale',
    initials: 'MC',
    author: 'Maya Chen',
    title: 'Chief Technology Officer',
    company: 'Northstar Care Network',
    date: '2026-07-02',
    body: 'SynaptiVerse gave our team a reliable operational layer that stayed fast even when multiple departments reviewed queues at once. We cut manual routing time by 42% and finally had a workflow that clinical and administrative teams could trust during peak intake windows.',
  },
  {
    id: 'faster-product-rollout',
    initials: 'JE',
    author: 'Jordan Ellis',
    title: 'Lead Product Designer',
    company: 'CareOps Studio',
    date: '2026-06-24',
    body: 'The product experience feels calm, clear, and remarkably quick for a healthcare platform with so many roles. Our prototype review cycles moved twice as fast because stakeholders could understand patient, specialist, pharmacy, and lab journeys without extra explanation.',
  },
  {
    id: 'cost-efficient-ops',
    initials: 'AK',
    author: 'Ari Khan',
    title: 'Head of Finance',
    company: 'Meridian Health Partners',
    date: '2026-06-18',
    body: 'The strongest result for us was cost efficiency without a drop in quality. Consolidating fragmented dashboards into one coordinated interface helped us identify avoidable handoffs and project a 28% reduction in support overhead for the next operating cycle.',
  },
  {
    id: 'clinical-ops-confidence',
    initials: 'ST',
    author: 'Simone Taylor',
    title: 'Director of Clinical Operations',
    company: 'Atlas Medical Group',
    date: '2026-06-10',
    body: 'Our operations leaders loved how quickly the platform made waiting lists, appointments, and follow-up tasks easier to scan. The empty, loading, and notification states feel intentional, which gives teams confidence even before all backend integrations are live.',
  },
  {
    id: 'enterprise-ready-speed',
    initials: 'DL',
    author: 'Daniel Lawson',
    title: 'VP of Platform Strategy',
    company: 'Civic Health Systems',
    date: '2026-05-29',
    body: 'SynaptiVerse impressed us with speed, consistency, and a clean path toward enterprise integration. The frontend-only demo let our executives evaluate the network model in a single session, while the architecture kept the door open for secure APIs and real-time data.',
  },
] as const;

function formatDate(value?: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date);
}

function StarRating({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-1" aria-label={label}>
      {Array.from({ length: 5 }, (_, index) => (
        <Star key={`star-${index}`} className="h-4 w-4 fill-[#2563EB] text-[#2563EB]" aria-hidden="true" />
      ))}
    </div>
  );
}

function ReviewsSection() {
  return (
    <section className="bg-white px-6 pb-24" aria-labelledby="reviews-heading">
      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">User Reviews</p>
          <h2 id="reviews-heading" className="font-display mt-3 text-4xl text-[#0F172A]">Testimonial articles from teams building faster</h2>
          <p className="mt-4 text-base leading-7 text-slate-600">Detailed feedback from product, finance, and operations leaders evaluating SynaptiVerse for reliability, speed, and cost efficiency.</p>
        </div>
        <div className="mt-12 grid gap-5 md:grid-cols-2">
          {reviews.map((review) => (
            <article key={review.id} id={review.id} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <header className="space-y-4">
                <StarRating label="5 out of 5 star rating" />
                <div className="flex items-center gap-4">
                  <div
                    role="img"
                    aria-label={`Profile photo placeholder for ${review.author}`}
                    data-alt={`Profile photo placeholder for ${review.author}`}
                    className="grid h-14 w-14 shrink-0 place-items-center rounded-full border-2 border-dashed border-slate-300 bg-slate-100 text-sm font-black text-[#2563EB]"
                  >
                    {review.initials}
                  </div>
                  <div>
                    <h3 className="text-base font-black text-[#0F172A]">{review.author}</h3>
                    <p className="text-sm text-slate-600">{review.title}</p>
                    <p className="text-xs font-semibold text-[#2563EB]">{review.company}</p>
                  </div>
                </div>
              </header>
              <p className="mt-5 text-sm leading-7 text-slate-700">{review.body}</p>
              <footer className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
                <time dateTime={review.date} className="text-xs font-semibold text-slate-400">{formatDate(review.date)}</time>
                <Link href={`/blog#${review.id}`} className="inline-flex items-center gap-2 text-sm font-bold text-[#2563EB] transition-colors duration-200 hover:text-[#1D4ED8]" aria-label={`Read full case study for ${review.author} at ${review.company}`}>
                  Read full case study
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </footer>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function BlogPage() {
  const [blogPosts, setBlogPosts] = useState<BlogPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadPosts() {
      try {
        const data = await api.get('/api/v1/public/blog-posts');
        if (!cancelled) setBlogPosts(Array.isArray(data) ? (data as BlogPost[]) : []);
      } catch (error) {
        console.error(error);
        if (!cancelled) setBlogPosts([]);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadPosts();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="bg-slate-50 text-[#0F172A]">
      <Navbar />
      <section className="px-6 pb-16 pt-32 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Health Insights</p>
        <h1 className="font-display mt-3 text-5xl text-[#0F172A]">Latest health updates</h1>
      </section>
      <section className="px-6 pb-20" aria-labelledby="articles-heading">
        <h2 id="articles-heading" className="sr-only">Published articles</h2>
        <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
          {isLoading ? (
            [1, 2, 3].map((item) => <div key={item} className="h-80 animate-pulse rounded-lg bg-white" />)
          ) : blogPosts.length === 0 ? (
            <div className="col-span-3 py-16 text-center text-slate-400">
              <p>No articles published yet. Check back soon.</p>
            </div>
          ) : (
            blogPosts.map((post) => (
              <article key={post.id ?? post.title} className="overflow-hidden rounded-lg border border-slate-100 bg-white shadow-sm transition hover:shadow-md">
                <div className="grid h-48 place-items-center bg-gradient-to-br from-blue-50 to-slate-100 text-[#2563EB]"><FileText className="h-14 w-14 opacity-40" /></div>
                <div className="p-5">
                  {post.category ? <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-[#2563EB]">{post.category}</span> : null}
                  {post.published_at ? <p className="mt-4 text-xs text-slate-400">{formatDate(post.published_at)}</p> : null}
                  <h2 className="mt-2 font-semibold leading-snug text-[#0F172A]">{post.title}</h2>
                  {post.excerpt ? <p className="mt-2 text-sm leading-6 text-slate-500">{post.excerpt}</p> : null}
                </div>
              </article>
            ))
          )}
        </div>
      </section>
      <ReviewsSection />
      <Footer />
    </main>
  );
}
