import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import salesAgentService from '@/services/salesAgentService';
import sessionStore from '@/lib/session';
import Navbar from '@/components/Navbar.jsx';

const OrdersPage = () => {
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const customerId = sessionStore.getCustomerId();

  useEffect(() => {
    let mounted = true;
    const fetch = async () => {
      setLoading(true);
      try {
        const res = await salesAgentService.getOrders(customerId);
        if (!mounted) return;
        setOrders(res.orders || res || []);
      } catch (e) {
        console.error('Failed to fetch orders', e);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetch();
    return () => { mounted = false; };
  }, [customerId]);

  const current = orders.filter(o => (o.status || '').toLowerCase() !== 'delivered');
  const delivered = orders.filter(o => (o.status || '').toLowerCase() === 'delivered');

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 pt-28 pb-12">
        <h1 className="text-2xl font-bold mb-4">Your Orders</h1>
        {loading ? (
          <p>Loading orders...</p>
        ) : (
          <div className="space-y-6">
            <section>
              <h2 className="text-lg font-semibold mb-2">Current Orders</h2>
              {current.length === 0 ? <p className="text-sm text-gray-500">No current orders</p> : (
                <div className="space-y-3">
                  {current.map((o) => (
                    <div key={o.order_id || o.id} className="p-4 bg-white rounded shadow flex justify-between items-center">
                      <div>
                        <div className="font-semibold">{o.order_id || o.id}</div>
                        <div className="text-sm text-gray-500">{o.status || 'Processing'}</div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => navigate(`/orders/${o.order_id || o.id}`)} className="px-3 py-2 bg-blue-600 text-white rounded">View</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section>
              <h2 className="text-lg font-semibold mb-2">Delivered Orders</h2>
              {delivered.length === 0 ? <p className="text-sm text-gray-500">No delivered orders</p> : (
                <div className="space-y-3">
                  {delivered.map((o) => (
                    <div key={o.order_id || o.id} className="p-4 bg-white rounded shadow flex justify-between items-center">
                      <div>
                        <div className="font-semibold">{o.order_id || o.id}</div>
                        <div className="text-sm text-gray-500">Delivered</div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => navigate(`/orders/${o.order_id || o.id}`)} className="px-3 py-2 bg-blue-600 text-white rounded">View</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrdersPage;
