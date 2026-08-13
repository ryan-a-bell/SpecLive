import type { ReactNode } from "react";

interface PanelProps {
  title: string;
  subtitle?: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function Panel({ title, subtitle, aside, children, className, bodyClassName }: PanelProps) {
  return (
    <section className={`panel flex min-h-0 flex-col ${className ?? ""}`}>
      <header className="panel-header">
        <div>
          <div className="panel-title">{title}</div>
          {subtitle ? <div className="panel-subtitle">{subtitle}</div> : null}
        </div>
        {aside}
      </header>
      <div className={`panel-body min-h-0 flex-1 overflow-auto ${bodyClassName ?? ""}`}>
        {children}
      </div>
    </section>
  );
}
