import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import salesAgentService from '@/services/salesAgentService';
import postPurchaseService from '@/services/postPurchaseService';
import sessionStore from '@/lib/session';
import Navbar from '@/components/Navbar.jsx';

const OrderDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stylist, setStylist] = useState(null);
  const customerId = sessionStore.getCustomerId();

  useEffect(() => {
    let mounted = true;
    const fetchOrder = async () => {
      setLoading(true);
      try {
        const res = await salesAgentService.getOrders();
        const list = res.orders || res || [];
        const found = list.find(o => (o.order_id || o.id) === id);
        if (mounted) setOrder(found || { order_id: id, items: [] });
      } catch (e) {
        console.error('Failed to fetch order', e);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchOrder();
    return () => { mounted = false; };
  }, [id]);

  const requestStyling = async () => {
    if (!order) return;
    try {
      const payload = {
        customer_id: customerId,
        order_id: order.order_id || order.id,
        items: order.items || [],
      };
      const res = await salesAgentService.getStylistSuggestions(payload);
      setStylist(res.recommendations || res || null);
    } catch (e) {
      console.error('Stylist request failed', e);
      setStylist({ error: e.message });
    }
  };

  const openPostPurchase = async () => {
    // For simplicity navigate to chat and open post-purchase flow via Chat component triggers
    try {
      const payload = {
        order_id: order.order_id || order.id,
        customer_id: customerId,
        items: order.items || [],
      };
      await postPurchaseService.registerPostPurchaseOrder(payload);
      navigate('/chat');
    } catch (e) {
      console.error('Failed to register post-purchase order', e);
      navigate('/chat');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 pt-28 pb-12">
        <button onClick={() => navigate('/orders')} className="text-sm text-blue-600 mb-4">Back to orders</button>
        {loading ? <p>Loading...</p> : (
          <div className="bg-white rounded p-6 shadow">
            <h2 className="text-xl font-bold mb-2">Order {order?.order_id || id}</h2>
            <p className="text-sm text-gray-600 mb-4">Status: {order?.status || 'Processing'}</p>

            <div className="space-y-3">
              {(order?.items || []).map((it) => (
                <div key={it.sku || it.id} className="flex justify-between items-center p-3 border rounded">
                  <div>
                    <div className="font-medium">{it.name || it.sku}</div>
                    <div className="text-sm text-gray-500">SKU: {it.sku}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold">Qty: {it.qty}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 flex gap-3">
              <button onClick={openPostPurchase} className="px-4 py-2 bg-yellow-600 text-white rounded">Post-Purchase</button>
              <button onClick={requestStyling} className="px-4 py-2 bg-pink-600 text-white rounded">Ask Stylist</button>
            </div>

            {stylist && (
              <div className="mt-6 p-4 bg-gray-50 rounded">
                <h3 className="font-semibold">Stylist Suggestions</h3>
                {stylist.error ? <p className="text-sm text-red-600">{stylist.error}</p> : (
                  <ul className="mt-2 list-disc pl-5">
                    {(stylist.recommendations || stylist || []).map((r, i) => (
                      <li key={i} className="text-sm">{typeof r === 'string' ? r : JSON.stringify(r)}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default OrderDetailPage;
