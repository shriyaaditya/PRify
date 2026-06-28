import Link from "next/link";

export function Sidebar() {
  return (
    <div className="w-64 bg-slate-900 text-white min-h-screen p-4">
      <div className="text-xl font-bold mb-8">PRify</div>
      <nav className="flex flex-col space-y-4">
        <Link href="/dashboard" className="hover:text-gray-300">Dashboard</Link>
        <Link href="/repositories" className="hover:text-gray-300">Repositories</Link>
        <Link href="/reviews" className="hover:text-gray-300">Reviews</Link>
        <Link href="/settings" className="hover:text-gray-300">Settings</Link>
      </nav>
    </div>
  );
}
