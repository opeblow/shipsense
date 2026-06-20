import { useEffect, useState } from 'react';
import { Outlet, useSearchParams } from 'react-router-dom';
import Sidebar from './Sidebar';
import { getProduct } from '../api/client';

export default function DashboardLayout() {
  const [searchParams] = useSearchParams();
  const productId = searchParams.get('productId');
  const [sampleProductId, setSampleProductId] = useState(null);

  useEffect(() => {
    if (!productId) return;
    let cancelled = false;
    getProduct(productId)
      .then((product) => {
        if (!cancelled) {
          setSampleProductId(product.is_sample ? productId : null);
        }
      })
      .catch(() => {
        if (!cancelled) setSampleProductId(null);
      });
    return () => { cancelled = true; };
  }, [productId]);

  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar />
      <main className="flex-1 min-w-0 overflow-auto">
        {sampleProductId === productId && (
          <div className="border-b border-warning/30 bg-warning/10 px-8 py-2 text-center">
            <p className="text-xs font-medium text-warning">
              Sample workspace — behavioral events and experiment results are synthetic demonstration data.
            </p>
          </div>
        )}
        <div className="max-w-5xl mx-auto px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
