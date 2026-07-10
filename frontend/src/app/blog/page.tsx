'use client';

import { useEffect, useState } from 'react';
import { FileText } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { api } from '@/lib/auth';

type BlogPost = { id?: string; title?: string; category?: string; excerpt?: string; published_at?: string };

function formatDate(value?: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date);
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
    <main className="bg-slate-50">
      <Navbar />
      <section className="px-6 pb-16 pt-32 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Health Insights</p>
        <h1 className="font-display mt-3 text-5xl text-slate-900">Latest health updates</h1>
      </section>
      <section className="px-6 pb-20">
        <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
          {isLoading ? (
            [1, 2, 3].map((item) => <div key={item} className="h-80 animate-pulse rounded-2xl bg-white" />)
          ) : blogPosts.length === 0 ? (
            <div className="col-span-3 py-16 text-center text-slate-400">
              <p>No articles published yet. Check back soon.</p>
            </div>
          ) : (
            blogPosts.map((post) => (
              <article key={post.id ?? post.title} className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm transition hover:shadow-md">
                <div className="grid h-48 place-items-center bg-gradient-to-br from-blue-50 to-slate-100 text-[#2563EB]"><FileText className="h-14 w-14 opacity-40" /></div>
                <div className="p-5">
                  {post.category ? <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-[#2563EB]">{post.category}</span> : null}
                  {post.published_at ? <p className="mt-4 text-xs text-slate-400">{formatDate(post.published_at)}</p> : null}
                  <h2 className="mt-2 font-semibold leading-snug text-slate-900">{post.title}</h2>
                  {post.excerpt ? <p className="mt-2 text-sm leading-6 text-slate-500">{post.excerpt}</p> : null}
                </div>
              </article>
            ))
          )}
        </div>
      </section>
      <Footer />
    </main>
  );
}
