export function Navbar() {
  return (
    <div className="h-16 bg-white border-b flex items-center px-6 justify-between">
      <div className="font-semibold text-gray-700">PRify Dashboard</div>
      <div>
        <button className="text-sm font-medium text-gray-600 hover:text-gray-900">Sign Out</button>
      </div>
    </div>
  );
}
