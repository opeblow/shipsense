import { useState } from 'react';

export default function Table({ columns, data, sortable = true }) {
  const [sort, setSort] = useState({ key: null, dir: 'asc' });

  const handleSort = (key) => {
    if (!sortable) return;
    setSort((prev) => ({
      key,
      dir: prev.key === key && prev.dir === 'asc' ? 'desc' : 'asc',
    }));
  };

  const sorted = sort.key
    ? [...data].sort((a, b) => {
        const av = a[sort.key];
        const bv = b[sort.key];
        const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv));
        return sort.dir === 'asc' ? cmp : -cmp;
      })
    : data;

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-border">
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className={`text-left py-3 px-4 text-xs font-medium text-text-secondary uppercase tracking-wider
                  ${sortable ? 'cursor-pointer hover:text-text select-none' : ''}`}
              >
                <span className="flex items-center gap-1">
                  {col.label}
                  {sort.key === col.key && (
                    <span className="text-accent text-[10px]">{sort.dir === 'asc' ? '\u25B2' : '\u25BC'}</span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr
              key={row.id ?? i}
              className={`border-b border-border ${i % 2 === 1 ? 'bg-zebra' : ''} hover:bg-zebra transition-colors duration-75`}
            >
              {columns.map((col) => (
                <td key={col.key} className="py-3 px-4 text-text">
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
