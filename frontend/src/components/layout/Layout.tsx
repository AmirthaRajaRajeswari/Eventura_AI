import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Left sidebar */}
      <Sidebar />

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopNav />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
