import { ReactNode } from "react";
import PageLayout from "@/components/PageLayout";

export default function StaticPage({ title, intro, children }: { title: string; intro?: string; children: ReactNode }) {
  return (
    <PageLayout>
      <section className="bg-background-alt border-b border-border">
        <div className="container-page py-14">
          <h1 className="text-4xl md:text-5xl font-extrabold text-primary">{title}</h1>
          {intro && <p className="mt-4 text-lg text-muted-foreground max-w-2xl">{intro}</p>}
        </div>
      </section>
      <section className="container-page py-12 max-w-3xl">
        <div className="prose prose-slate max-w-none text-foreground">{children}</div>
      </section>
    </PageLayout>
  );
}
