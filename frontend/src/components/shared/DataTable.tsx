import { Badge } from '@/components/shared/Badge';

type DataTableProps = {
  columns: string[];
  rows: (string | number)[][];
};

export function DataTable({ columns, rows }: DataTableProps) {
  return (
    <div className="overflow-hidden rounded-[22px] border border-[#dbe3ef] bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-100">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th key={column} className="px-7 py-5 text-left text-xs font-extrabold uppercase tracking-[0.12em] text-[#8a97b4]">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => (
              <tr key={row.join('-')} className="hover:bg-slate-50/60">
                {row.map((cell, index) => (
                  <td key={`${row.join('-')}-${index}`} className="px-7 py-5 text-base text-[#526783]">
                    {index === row.length - 1 ? <Badge tone="success">{cell}</Badge> : cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
