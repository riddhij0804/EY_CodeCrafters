// Service Integration Test Component
// Use this to test all backend services

import { useState } from 'react';
import {
  inventoryService,
  loyaltyService,
  paymentService,
  postPurchaseService,
  fulfillmentService,
} from '../services';

const ServiceTest = () => {
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(false);

  const addResult = (service, result) => {
    setResults(prev => ({
      ...prev,
      [service]: result
    }));
  };

  const testInventory = async () => {
    setLoading(true);
    try {
      const result = await inventoryService.getInventory('SKU001');
      addResult('inventory', { success: true, data: result });
    } catch (error) {
      addResult('inventory', { success: false, error: error.message });
    }
    setLoading(false);
  };

  const testLoyalty = async () => {
    setLoading(true);
    try {
      const result = await loyaltyService.getLoyaltyPoints('user123');
      addResult('loyalty', { success: true, data: result });
    } catch (error) {
      addResult('loyalty', { success: false, error: error.message });
    }
    setLoading(false);
  };

  const testPayment = async () => {
    setLoading(true);
    try {
      const result = await paymentService.getPaymentMethods();
      addResult('payment', { success: true, data: result });
    } catch (error) {
      addResult('payment', { success: false, error: error.message });
    }
    setLoading(false);
  };

  const testPostPurchase = async () => {
    setLoading(true);
    try {
      const result = await postPurchaseService.getReturnReasons();
      addResult('postPurchase', { success: true, data: result });
    } catch (error) {
      addResult('postPurchase', { success: false, error: error.message });
    }
    setLoading(false);
  };

  const testFulfillment = async () => {
    setLoading(true);
    try {
      const result = await fulfillmentService.getFulfillmentStatus('ORD123');
      addResult('fulfillment', { success: true, data: result });
    } catch (error) {
      addResult('fulfillment', { success: false, error: error.message });
    }
    setLoading(false);
  };

  const testAll = async () => {
    await testInventory();
    await testLoyalty();
    await testPayment();
    await testPostPurchase();
    await testFulfillment();
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Backend Service Tests</h1>
      
      <div className="grid grid-cols-2 gap-4 mb-6">
        <button
          onClick={testInventory}
          disabled={loading}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
        >
          Test Inventory
        </button>
        <button
          onClick={testLoyalty}
          disabled={loading}
          className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 disabled:opacity-50"
        >
          Test Loyalty
        </button>
        <button
          onClick={testPayment}
          disabled={loading}
          className="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600 disabled:opacity-50"
        >
          Test Payment
        </button>
        <button
          onClick={testPostPurchase}
          disabled={loading}
          className="bg-orange-500 text-white px-4 py-2 rounded hover:bg-orange-600 disabled:opacity-50"
        >
          Test Post-Purchase
        </button>
        <button
          onClick={testFulfillment}
          disabled={loading}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 disabled:opacity-50"
        >
          Test Fulfillment
        </button>
        <button
          onClick={testAll}
          disabled={loading}
          className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-gray-900 disabled:opacity-50"
        >
          Test All Services
        </button>
      </div>

      <div className="space-y-4">
        {Object.entries(results).map(([service, result]) => (
          <div
            key={service}
            className={`p-4 rounded border ${
              result.success ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'
            }`}
          >
            <h3 className="font-bold text-lg capitalize mb-2">{service}</h3>
            {result.success ? (
              <pre className="text-sm overflow-auto">
                {JSON.stringify(result.data, null, 2)}
              </pre>
            ) : (
              <p className="text-red-600">{result.error}</p>
            )}
          </div>
        ))}
      </div>

      {loading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-4 rounded">Testing...</div>
        </div>
      )}
    </div>
  );
};

export default ServiceTest;
