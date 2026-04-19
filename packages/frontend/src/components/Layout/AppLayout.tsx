import React from "react";
import { Outlet } from "react-router-dom";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-[#0f1419] text-white">
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 min-h-[calc(100vh-64px)] overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
