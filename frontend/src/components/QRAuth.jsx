import { useState } from 'react';
import { QrCode, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import authService from '../services/authService';
import sessionStore from '../lib/session';

/**
 * QR Auth Component for Kiosk Authentication
 * 
 * This component allows logged-in users to generate a QR code
 * that can be scanned by kiosk devices for quick authentication.
 * 
 * Features:
 * - Generate QR token (15-minute expiry)
 * - Display QR code for scanning
 * - Auto-refresh before expiry
 * - Scan instructions
 */

const QRAuth = () => {
  const [showModal, setShowModal] = useState(false);
  const [qrToken, setQrToken] = useState(null);
  const [qrCodeUrl, setQrCodeUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expiryTime, setExpiryTime] = useState(null);

  const generateQRCode = async () => {
    setLoading(true);
    setError('');

    try {
      const sessionToken = sessionStore.getSessionToken();
      const phone = sessionStore.getPhone();

      if (!sessionToken || !phone) {
        setError('Please login first to generate QR code');
        setLoading(false);
        return;
      }

      // Call backend to generate QR token
      const response = await authService.initQRAuth(phone, sessionToken);

      if (response.success) {
        const token = response.qr_token;
        setQrToken(token);

        // Calculate expiry time
        const expiresAt = new Date(Date.now() + response.expires_in_seconds * 1000);
        setExpiryTime(expiresAt);

        // Generate QR code URL using a QR code API
        // Using goqr.me API (free, no registration required)
        const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(token)}`;
        setQrCodeUrl(qrUrl);

        setShowModal(true);
      } else {
        setError('Failed to generate QR code');
      }
    } catch (err) {
      setError(err.message || 'Failed to generate QR code');
    } finally {
      setLoading(false);
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setQrToken(null);
    setQrCodeUrl(null);
    setError('');
    setExpiryTime(null);
  };

  const handleClick = () => {
    if (!sessionStore.getSessionToken()) {
      setError('Please login to generate QR code');
      return;
    }
    generateQRCode();
  };

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={handleClick}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-red-600 to-orange-500 text-white rounded-lg font-medium hover:from-red-500 hover:to-orange-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md"
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <QrCode className="w-5 h-5" />
            Generate Kiosk QR
          </>
        )}
      </button>

      {/* Error Display */}
      {error && !showModal && (
        <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 text-sm text-red-700">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* QR Code Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-red-600 to-orange-500 px-6 py-4 flex items-center justify-between">
              <div>
                <h3 className="text-xl font-semibold text-white">Kiosk QR Code</h3>
                <p className="text-sm text-orange-100">Scan to login on kiosk</p>
              </div>
              <button
                onClick={closeModal}
                className="p-2 hover:bg-white/10 rounded-full transition"
              >
                <X className="w-5 h-5 text-white" />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 space-y-4">
              {qrCodeUrl ? (
                <>
                  {/* QR Code Display */}
                  <div className="flex justify-center">
                    <div className="p-4 bg-white border-4 border-red-100 rounded-xl shadow-lg">
                      <img
                        src={qrCodeUrl}
                        alt="Kiosk QR Code"
                        className="w-64 h-64"
                      />
                    </div>
                  </div>

                  {/* Instructions */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start gap-2">
                      <CheckCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-blue-900">
                        <p className="font-semibold mb-1">How to use:</p>
                        <ol className="list-decimal list-inside space-y-1 text-blue-800">
                          <li>Open the kiosk app</li>
                          <li>Select "Scan QR Code" option</li>
                          <li>Point camera at this QR code</li>
                          <li>Your session will be active on kiosk</li>
                        </ol>
                      </div>
                    </div>
                  </div>

                  {/* Expiry Info */}
                  {expiryTime && (
                    <div className="text-center text-sm text-gray-600">
                      <p>
                        This QR code expires at{' '}
                        <span className="font-semibold text-red-600">
                          {expiryTime.toLocaleTimeString()}
                        </span>
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        Valid for 15 minutes from generation
                      </p>
                    </div>
                  )}

                  {/* Security Note */}
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <p className="text-xs text-yellow-800">
                      <strong>Security Note:</strong> Do not share this QR code with anyone. 
                      It provides full access to your account on kiosk devices.
                    </p>
                  </div>
                </>
              ) : (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-red-600" />
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3">
              <button
                onClick={closeModal}
                className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg font-medium transition"
              >
                Close
              </button>
              <button
                onClick={generateQRCode}
                disabled={loading}
                className="px-4 py-2 bg-gradient-to-r from-red-600 to-orange-500 text-white rounded-lg font-medium hover:from-red-500 hover:to-orange-400 disabled:opacity-50 transition"
              >
                Regenerate
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default QRAuth;
