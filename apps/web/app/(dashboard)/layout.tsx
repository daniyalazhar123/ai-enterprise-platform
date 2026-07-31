import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <Header />
      <Sidebar />
      <main className="pl-56 pt-14">
        <div className="container py-6">{children}</div>
      </main>
    </div>
  );
}