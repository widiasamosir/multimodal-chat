export default function MediaSection({
                          title,
                          items,
                          type,
                      }: {
    title: string;
    items: any[];
    type: "image" | "table";
}) {
    return (
        <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">
                {title} ({items.length})
            </h2>
            <div className={type === "image" ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" : "space-y-4"}>
                {items.map((item) => (
                    <div key={item.id} className="border rounded-lg p-4">
                        <img
                            src={`http://localhost:8000${item.url}`}
                            alt={item.caption || `${type} from page ${item.page}`}
                            className="w-full rounded mb-2"
                        />
                        <p className="text-sm text-gray-600">{item.caption || `${type.charAt(0).toUpperCase() + type.slice(1)} from page ${item.page}`}</p>
                        {type === "image" ? (
                            <p className="text-xs text-gray-500">Page {item.page} • {item.width}x{item.height}px</p>
                        ) : (
                            <p className="text-xs text-gray-500">Page {item.page} • {item.rows} rows × {item.columns} columns</p>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}