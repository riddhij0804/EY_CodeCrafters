import { useState, useRef, useEffect } from 'react';
import { Send, Check, CheckCheck, Phone, Video, Mic, MicOff, User, X, CreditCard, LifeBuoy } from 'lucide-react';
import { createRazorpayOrder, verifyRazorpayPayment } from '../services/paymentService';
import { getTierInfo } from '../services/loyaltyService';
import API_ENDPOINTS from '../config/api';
import sessionStore from '../lib/session';
import salesAgentService from '../services/salesAgentService';
import {
  getReturnReasons,
  getIssueTypes,
  initiateReturn,
  initiateExchange,
  raiseComplaint,
  submitFeedback,
  registerPostPurchaseOrder,
} from '../services/postPurchaseService';

const SESSION_API = API_ENDPOINTS.SESSION_MANAGER;
const SALES_API = API_ENDPOINTS.SALES_AGENT;

const parsePriceToNumber = (value) => {
  if (value === null || value === undefined) {
    return null;
  }

  const numeric = parseFloat(String(value).replace(/[^0-9.]/g, ''));
  if (!Number.isFinite(numeric)) {
    return null;
  }

  return Number(Math.round(numeric * 100) / 100);
};

const formatINR = (amount) => {
  if (!Number.isFinite(amount)) {
    return '₹0';
  }

  return amount.toLocaleString('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: amount % 1 === 0 ? 0 : 2,
  });
};

const buildCheckoutOrderId = (sku = '') => {
  const safeSku = sku ? String(sku).replace(/[^A-Za-z0-9]/g, '').toUpperCase() : 'ITEM';
  return `ORDER-${safeSku}-${Date.now()}`;
};

const extractCardAttribute = (card, key) => {
  if (!card) return '';
  if (card[key]) return card[key];

  const { attributes } = card;
  if (!attributes) return '';

  if (typeof attributes === 'object' && attributes !== null && attributes[key]) {
    return attributes[key];
  }

  if (typeof attributes === 'string') {
    try {
      const parsed = JSON.parse(attributes);
      if (parsed && typeof parsed === 'object' && parsed[key]) {
        return parsed[key];
      }
    } catch (error) {
      try {
        const normalized = attributes.replace(/'/g, '"');
        const parsed = JSON.parse(normalized);
        if (parsed && typeof parsed === 'object' && parsed[key]) {
          return parsed[key];
        }
      } catch (secondaryError) {
        console.warn('Failed to parse card attributes', secondaryError);
      }
    }
  }

  return '';
};

const SUPPORT_TITLES = {
  menu: 'Post-Purchase Support',
  return: 'Start a Return',
  exchange: 'Request an Exchange',
  complaint: 'Raise a Complaint',
  feedback: 'Share Feedback',
};

const Chat = () => {
  // Session state
  const [sessionInfo, setSessionInfo] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [showPhoneInput, setShowPhoneInput] = useState(true);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [loyaltyPoints, setLoyaltyPoints] = useState(0);
  const [loyaltyTier, setLoyaltyTier] = useState('Bronze');
  const [userId, setUserId] = useState(null);

  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [expandedMessages, setExpandedMessages] = useState(new Set());
  const [expandedCards, setExpandedCards] = useState(new Set());
  const [isRazorpayReady, setIsRazorpayReady] = useState(false);
  const [isPaymentProcessing, setIsPaymentProcessing] = useState(false);
  const [pendingCheckoutItem, setPendingCheckoutItem] = useState(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [lastCompletedOrder, setLastCompletedOrder] = useState(null);
  const [showSupportPanel, setShowSupportPanel] = useState(false);
  const [activeSupportMode, setActiveSupportMode] = useState(null);
  const [supportForm, setSupportForm] = useState({});
  const [supportContext, setSupportContext] = useState({});
  const [returnReasons, setReturnReasons] = useState([]);
  const [issueTypes, setIssueTypes] = useState([]);
  const [panelInitializing, setPanelInitializing] = useState(false);
  const [supportLoading, setSupportLoading] = useState(false);
  const [supportResult, setSupportResult] = useState(null);
  const [supportError, setSupportError] = useState('');
  const [showAddressModal, setShowAddressModal] = useState(false);
  const [addressForm, setAddressForm] = useState({ city: '', landmark: '', building: '' });
  const [addressError, setAddressError] = useState('');
  const [savedAddress, setSavedAddress] = useState(null);
  const [pendingPaymentDetails, setPendingPaymentDetails] = useState(null);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const transcriptRef = useRef('');
  const paymentInFlightRef = useRef(false);

  const supportActions = [
    { key: 'return', label: 'Start Return', caption: 'Schedule pickup and refund', emoji: '📦' },
    { key: 'exchange', label: 'Exchange Size', caption: 'Swap for a better fit', emoji: '🔁' },
    { key: 'complaint', label: 'Raise Complaint', caption: 'Escalate delivery or product issues', emoji: '📝' },
    { key: 'feedback', label: 'Share Feedback', caption: 'Tell us how we did', emoji: '💬' },
  ];

  useEffect(() => {
    const storedAddress = sessionStore.getAddress?.();
    if (storedAddress) {
      setSavedAddress(storedAddress);
      setAddressForm({
        city: storedAddress.city || '',
        landmark: storedAddress.landmark || '',
        building: storedAddress.building || '',
      });
    }
  }, []);

  // Helper to normalize surrounding quotes from messages so we only add one pair
  const normalizeQuotes = (text) => {
    if (!text) return '';
    return String(text).replace(/^\s*["'“”]+|["'“”]+\s*$/g, '').trim();
  };

  // Loyalty Management
  const fetchLoyaltyPoints = async (user_id) => {
    try {
      const result = await getTierInfo(user_id);
      if (result && result.points !== undefined) {
        setLoyaltyPoints(result.points);
        setLoyaltyTier(result.tier || 'Bronze');
      }
    } catch (error) {
      console.error('Failed to fetch loyalty info:', error);
      // Gracefully handle error - set defaults so UI doesn't break
      setLoyaltyPoints(0);
      setLoyaltyTier('Bronze');
    }
  };

  // Session Management Functions
  const startOrRestoreSession = async (phone) => {
    setIsLoadingSession(true);
    try {
      const storedPhone = sessionStore.getPhone();
      const storedToken = sessionStore.getSessionToken();

      if (storedPhone === phone && storedToken) {
        // Try to restore existing session for this phone
        try {
          const restoreResp = await fetch(`${SESSION_API}/session/restore`, {
            method: 'GET',
            headers: { 'X-Session-Token': storedToken }
          });

          if (restoreResp.ok) {
            const restoreData = await restoreResp.json();
            setSessionToken(storedToken);
            setSessionInfo(restoreData.session);
            setShowPhoneInput(false);
            sessionStore.setPhone(phone);

            // Extract user_id and fetch loyalty points
            const user_id = restoreData.session.customer_id || restoreData.session.data?.user_id || restoreData.session.user_id || '101';
            setUserId(user_id);
            await fetchLoyaltyPoints(user_id);

            if (restoreData.session.data?.chat_context?.length > 0) {
                      const chatMessages = restoreData.session.data.chat_context.map((msg, idx) => ({
                        id: idx + 1,
                        text: msg.message,
                        sender: msg.sender === 'user' ? 'user' : 'agent',
                        timestamp: new Date(msg.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                        status: 'read',
                        cards: msg.metadata?.cards || []
                      }));
              setMessages(chatMessages);
            }
            setIsLoadingSession(false);
            return;
          }
        } catch (err) {
          console.warn('Stored session restore failed, falling back to start', err);
        }

      }

      // Start new session for this phone
      const response = await fetch(`${SESSION_API}/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone: phone,
          channel: 'whatsapp'
        })
      });

      if (!response.ok) throw new Error('Failed to start session');

      const data = await response.json();

      setSessionToken(data.session_token);
      sessionStore.setSessionToken(data.session_token);
      sessionStore.setPhone(phone);
      setSessionInfo(data.session);
      setShowPhoneInput(false);

      // Extract user_id and fetch loyalty points
      const user_id = data.session.customer_id || data.session.data?.user_id || data.session.user_id || '101';
      setUserId(user_id);
      await fetchLoyaltyPoints(user_id);

      // Load chat history from session
      if (data.session.data.chat_context && data.session.data.chat_context.length > 0) {
        const chatMessages = data.session.data.chat_context.map((msg, idx) => ({
          id: idx + 1,
          text: msg.message,
          sender: msg.sender === 'user' ? 'user' : 'agent',
          timestamp: new Date(msg.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          status: 'read'
        }));
        setMessages(chatMessages);
      } else {
        // Initial greeting
        setMessages([{
          id: 1,
          text: "Hello! I'm your AI Sales Agent. How can I help you today?",
          sender: 'agent',
          timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          status: 'read'
        }]);
      }
    } catch (error) {
      console.error('Session error:', error);
      alert('Failed to start session. Please try again.');
    } finally {
      setIsLoadingSession(false);
    }
  };

  const endSession = async () => {
    if (!sessionToken) return;

    try {
      await fetch(`${SESSION_API}/session/end`, {
        method: 'POST',
        headers: { 'X-Session-Token': sessionToken }
      });

      // Reset UI
      setSessionInfo(null);
      setSessionToken(null);
      sessionStore.clearAll();
      setMessages([]);
      setShowPhoneInput(true);
      setPhoneNumber('');
    } catch (error) {
      console.error('End session error:', error);
    }
  };

  const saveChatMessage = async (sender, message, metadata = null) => {
    if (!sessionToken) return;

    try {
      const payload = { sender, message };
      if (metadata) payload.metadata = metadata;

      await fetch(`${SESSION_API}/session/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': sessionToken
        },
        body: JSON.stringify({
          action: 'chat_message',
          payload
        })
      });
    } catch (error) {
      console.error('Failed to save chat message:', error);
    }
  };

  const appendAgentMessage = async (text, { metadata = null, messageProps = {} } = {}) => {
    const agentMessage = {
      id: Date.now() + Math.random(),
      text,
      sender: 'agent',
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      status: 'read',
      ...messageProps,
    };

    setMessages((prev) => [...prev, agentMessage]);
    await saveChatMessage('agent', text, metadata);
    return agentMessage;
  };

  const handleAddressInputChange = (field, value) => {
    setAddressForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const openAddressModalForPayment = (paymentConfig) => {
    if (!paymentConfig || !paymentConfig.amount) {
      alert('Payment details are missing. Please try again.');
      return;
    }

    const existing = savedAddress || sessionStore.getAddress?.() || {};
    setAddressForm({
      city: existing.city || '',
      landmark: existing.landmark || '',
      building: existing.building || '',
    });
    setAddressError('');
    setPendingPaymentDetails(paymentConfig);
    setShowAddressModal(true);
  };

  const closeAddressModal = () => {
    setShowAddressModal(false);
    setAddressError('');
    setPendingPaymentDetails(null);
    if (savedAddress) {
      setAddressForm({
        city: savedAddress.city || '',
        landmark: savedAddress.landmark || '',
        building: savedAddress.building || '',
      });
    }
  };

  const submitAddressForm = async (event) => {
    if (event && typeof event.preventDefault === 'function') {
      event.preventDefault();
    }

    const trimmedCity = (addressForm.city || '').trim();
    const trimmedLandmark = (addressForm.landmark || '').trim();
    const trimmedBuilding = (addressForm.building || '').trim();

    if (!trimmedCity || !trimmedLandmark || !trimmedBuilding) {
      setAddressError('City, landmark, and building are required.');
      return;
    }

    const normalizedAddress = {
      city: trimmedCity,
      landmark: trimmedLandmark,
      building: trimmedBuilding,
    };

    try {
      if (typeof sessionStore.setAddress === 'function') {
        sessionStore.setAddress(normalizedAddress);
      }
      setSavedAddress(normalizedAddress);
      setAddressForm(normalizedAddress);
      setSessionInfo((prev) => (
        prev
          ? {
              ...prev,
              data: {
                ...(prev.data || {}),
                shipping_address: normalizedAddress,
              },
            }
          : prev
      ));
      await saveChatMessage('user', 'Shared delivery address for this order.', {
        shipping_address: normalizedAddress,
      });
    } catch (storageError) {
      console.error('Failed to persist address:', storageError);
    }

    const paymentConfig = pendingPaymentDetails;
    setShowAddressModal(false);
    setPendingPaymentDetails(null);
    setAddressError('');

    if (!paymentConfig) {
      return;
    }

    await appendAgentMessage('📍 Address saved. Opening payment gateway now...');
    await initiateRazorpayPayment(paymentConfig.amount, {
      ...paymentConfig.details,
      address: normalizedAddress,
    });
  };

  const updateSupportForm = (field, value) => {
    setSupportForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const submitSupportForm = async (event) => {
    if (event && typeof event.preventDefault === 'function') {
      event.preventDefault();
    }

    if (!activeSupportMode || activeSupportMode === 'menu') {
      return;
    }

    setSupportLoading(true);
    setSupportError('');

    try {
      let result = null;
      let summaryText = '';

      switch (activeSupportMode) {
        case 'return': {
          if (!supportForm.user_id || !supportForm.order_id || !supportForm.product_sku || !supportForm.reason_code) {
            setSupportError('User, order, product, and reason are required.');
            setSupportLoading(false);
            return;
          }

          const images = Array.isArray(supportForm.images)
            ? supportForm.images
            : (supportForm.images
              ? supportForm.images.split(',').map((img) => img.trim()).filter(Boolean)
              : []);

          result = await initiateReturn({
            user_id: supportForm.user_id,
            order_id: supportForm.order_id,
            product_sku: supportForm.product_sku,
            reason_code: supportForm.reason_code,
            additional_comments: supportForm.additional_comments || '',
            images,
          });

          summaryText = `📦 Return ${result.return_id} created for order ${supportForm.order_id}. Pickup ${result.pickup_date || 'will be scheduled soon'} and refund will trigger after inspection.`;
          await appendAgentMessage(summaryText, {
            metadata: {
              post_purchase: {
                stage: 'return',
                return_id: result.return_id,
                order_id: supportForm.order_id,
                product_sku: supportForm.product_sku,
              },
            },
          });
          break;
        }
        case 'exchange': {
          if (!supportForm.user_id || !supportForm.order_id || !supportForm.product_sku || !supportForm.requested_size) {
            setSupportError('User, order, product, and requested size are required.');
            setSupportLoading(false);
            return;
          }

          result = await initiateExchange({
            user_id: supportForm.user_id,
            order_id: supportForm.order_id,
            product_sku: supportForm.product_sku,
            current_size: supportForm.current_size || '',
            requested_size: supportForm.requested_size,
            reason: supportForm.reason || '',
          });

          summaryText = `🔁 Exchange ${result.exchange_id} started for ${supportForm.product_sku}. New size arrives by ${result.delivery_date || 'the promised date'}.`;
          await appendAgentMessage(summaryText, {
            metadata: {
              post_purchase: {
                stage: 'exchange',
                exchange_id: result.exchange_id,
                order_id: supportForm.order_id,
                product_sku: supportForm.product_sku,
              },
            },
          });
          break;
        }
        case 'complaint': {
          if (!supportForm.user_id || !supportForm.issue_type || !supportForm.description) {
            setSupportError('Issue type and description are required.');
            setSupportLoading(false);
            return;
          }

          result = await raiseComplaint({
            user_id: supportForm.user_id,
            order_id: supportForm.order_id || '',
            issue_type: supportForm.issue_type,
            description: supportForm.description,
            priority: supportForm.priority || 'medium',
          });

          summaryText = `📝 Complaint ticket ${result.ticket_number} logged (${supportForm.issue_type}). We will reach out soon.`;
          await appendAgentMessage(summaryText, {
            metadata: {
              post_purchase: {
                stage: 'complaint',
                complaint_id: result.complaint_id,
                ticket_number: result.ticket_number,
              },
            },
          });
          break;
        }
        case 'feedback': {
          if (!supportForm.product_sku || !supportForm.size_purchased) {
            setSupportError('Product SKU and purchased size are required.');
            setSupportLoading(false);
            return;
          }

          result = await submitFeedback({
            user_id: supportForm.user_id,
            product_sku: supportForm.product_sku,
            size_purchased: supportForm.size_purchased,
            fit_rating: supportForm.fit_rating || 'perfect',
            length_feedback: supportForm.length_feedback || 'not_specified',
            comments: supportForm.comments || '',
          });

          summaryText = result.message
            ? `💬 ${result.message}`
            : '💬 Feedback saved. Thanks for helping us improve your next fit.';
          await appendAgentMessage(summaryText, {
            metadata: {
              post_purchase: {
                stage: 'feedback',
                product_sku: supportForm.product_sku,
              },
            },
          });
          break;
        }
        default:
          setSupportError('Please pick a support option.');
          setSupportLoading(false);
          return;
      }

      if (result) {
        setSupportResult({ type: activeSupportMode, data: result, summary: summaryText });
      }
    } catch (error) {
      console.error('Post-purchase request failed:', error);
      setSupportError(error.message || 'Action failed. Please try again.');
    } finally {
      setSupportLoading(false);
    }
  };

  // Auto-scroll to bottom when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Initialize Speech Recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        let finalTranscript = '';

        for (let i = 0; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          }
        }

        if (finalTranscript) {
          transcriptRef.current += finalTranscript;
          setInputText(transcriptRef.current);
        }
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
      };
    }
  }, []);

  useEffect(() => {
    if (window.Razorpay) {
      setIsRazorpayReady(true);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => setIsRazorpayReady(true);
    script.onerror = () => {
      console.error('Failed to load Razorpay checkout script');
      setIsRazorpayReady(false);
    };

    document.body.appendChild(script);

    return () => {
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };
  }, []);

  // Mock agent responses
  const mockAgentResponses = [
    "Sure! Let me check the best options for you.",
    "I found some great products that match your preferences!",
    "Would you like me to show you our top recommendations?",
    "I can help you with that. What's your budget?",
    "Great choice! Let me find similar items for you.",
    "I'm checking our inventory for you...",
    "Based on your preferences, I have some perfect options!"
  ];

  const initiateRazorpayPayment = async (amount, detailsArg = null) => {
    if (!sessionToken) {
      alert('Start a chat session before initiating payment.');
      return;
    }

    if (!window.Razorpay || !isRazorpayReady) {
      alert('Razorpay checkout is still loading. Please wait a moment and try again.');
      return;
    }

    const parsedAmount = parsePriceToNumber(amount);
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      alert('Unable to determine payment amount. Please verify the price and try again.');
      return;
    }

    setIsPaymentProcessing(true);
    paymentInFlightRef.current = true;

    try {
      const normalizedDetails = (detailsArg && typeof detailsArg === 'object') ? detailsArg : {};
      const productDetails = normalizedDetails.product || (normalizedDetails.name || normalizedDetails.sku ? normalizedDetails : null) || pendingCheckoutItem;
      const shippingAddress = normalizedDetails.address || savedAddress;
      const notes = {
        session_id: sessionInfo?.session_id || '',
        phone: sessionInfo?.phone || '',
      };

      if (sessionInfo?.data?.customer_id) {
        notes.customer_id = sessionInfo.data.customer_id;
      }
      if (productDetails?.sku) {
        notes.product_sku = productDetails.sku;
      }
      if (productDetails?.name) {
        notes.product_name = productDetails.name;
      }
      if (normalizedDetails.source) {
        notes.checkout_source = normalizedDetails.source;
      }
      if (shippingAddress) {
        notes.address_city = shippingAddress.city || '';
        notes.address_landmark = shippingAddress.landmark || '';
        notes.address_building = shippingAddress.building || '';
      }

      const orderPayload = {
        amount_rupees: parsedAmount,
        currency: 'INR',
        notes,
      };

      if (normalizedDetails.orderId) {
        orderPayload.receipt = normalizedDetails.orderId;
      }

      const orderResponse = await createRazorpayOrder(orderPayload);

      const options = {
        key: orderResponse.razorpay_key_id,
        amount: orderResponse.order.amount,
        currency: orderResponse.order.currency,
        name: 'EY CodeCrafters',
        description: productDetails?.name ? `Order for ${productDetails.name}` : 'AI Sales Agent Order',
        order_id: orderResponse.order.id,
        prefill: {
          name: sessionInfo?.data?.customer_name || sessionInfo?.phone || 'Customer',
          email: sessionInfo?.data?.email || 'test@example.com',
          contact: sessionInfo?.phone || '',
        },
        theme: { color: '#008069' },
        modal: {
          ondismiss: async () => {
            if (paymentInFlightRef.current) {
              const infoText = 'ℹ️ Razorpay checkout was closed before completing the payment.';
              const infoMessage = {
                id: Date.now() + Math.random(),
                text: infoText,
                sender: 'agent',
                timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                status: 'read',
              };
              setMessages((prev) => [...prev, infoMessage]);
              await saveChatMessage('agent', infoText);
            }
            paymentInFlightRef.current = false;
            setIsPaymentProcessing(false);
          },
        },
        handler: async (response) => {
          try {
            await verifyRazorpayPayment({
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_signature: response.razorpay_signature,
              amount_rupees: parsedAmount,
              user_id: sessionInfo?.data?.customer_id || sessionInfo?.phone,
              method: 'razorpay',
            });

            // Refresh loyalty points after payment
            await fetchLoyaltyPoints(userId);

            let successText = `✅ Payment of ₹${parsedAmount} received!\nPayment ID: ${response.razorpay_payment_id}`;
            
            // Add product-specific message and rewards
            if (productDetails) {
              successText += `\n\n🎉 Purchase Complete!\n📦 ${productDetails.name || 'Selected item'}\n💰 Amount Paid: ₹${parsedAmount}`;
              
              // Show rewards earned (this will be updated by the payment service)
              successText += `\n\n🎁 Rewards Earned:\n💎 Loyalty points added to your account!\n🏅 Check your updated tier status above.`;
            }

            const successMessage = {
              id: Date.now() + Math.random(),
              text: successText,
              sender: 'agent',
              timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
              status: 'read',
            };
            setMessages((prev) => [...prev, successMessage]);
            await saveChatMessage('agent', successText);
            const displayName = productDetails?.name || '';
            const productLine = displayName ? ` for ${displayName}` : '';
            await appendAgentMessage(
              `✅ Payment of ${formatINR(parsedAmount)} received${productLine}!\nPayment ID: ${response.razorpay_payment_id}`
            );

            const orderId = normalizedDetails.orderId || response.razorpay_order_id;
            const recordedAddress = normalizedDetails.address || savedAddress || null;

            if (productDetails) {
              const orderOwner = sessionInfo?.data?.customer_id || sessionInfo?.phone || '';
              const quantity = Number(productDetails.quantity) > 0 ? Number(productDetails.quantity) : 1;
              const unitPrice = Number(productDetails.price) || parsedAmount / quantity;
              const orderPayload = {
                order_id: orderId,
                user_id: orderOwner,
                amount: parsedAmount,
                status: 'completed',
                created_at: new Date().toISOString(),
                shipping_address: recordedAddress || {},
                metadata: {
                  payment_id: response.razorpay_payment_id,
                  razorpay_order_id: response.razorpay_order_id,
                  checkout_source: normalizedDetails.source || '',
                  session_id: sessionInfo?.session_id || '',
                },
                items: [
                  {
                    sku: productDetails.sku || 'UNKNOWN',
                    name: productDetails.name || 'Purchased item',
                    brand: productDetails.brand || '',
                    category: productDetails.category || productDetails.productType || '',
                    quantity,
                    unit_price: unitPrice,
                    line_total: unitPrice * quantity,
                  },
                ],
              };

              try {
                await registerPostPurchaseOrder(orderPayload);
              } catch (registerError) {
                console.error('Failed to register order for post-purchase:', registerError);
              }

              setLastCompletedOrder({
                orderId,
                amount: parsedAmount,
                paymentId: response.razorpay_payment_id,
                product: productDetails || undefined,
                address: recordedAddress,
              });

              if (productDetails?.sku) {
                try {
                  const stylistPayload = {
                    user_id: orderOwner || '',
                    product_sku: productDetails.sku || '',
                    product_name: productDetails.name || 'Purchased item',
                    category: productDetails.category || productDetails.productType || 'Apparel',
                    color: productDetails.color || '',
                    brand: productDetails.brand || '',
                  };

                  const stylistResponse = await salesAgentService.getStylistSuggestions(stylistPayload);
                  const stylistBundle = stylistResponse?.recommendations || {};
                  const recommendedProducts = Array.isArray(stylistBundle?.recommended_products)
                    ? stylistBundle.recommended_products
                        .map((item) => ({
                          sku: item?.sku || '',
                          name: item?.name || '',
                          reason: item?.reason || '',
                        }))
                        .filter((item) => item.sku || item.name || item.reason)
                    : [];
                  const stylingTips = Array.isArray(stylistBundle?.styling_tips)
                    ? stylistBundle.styling_tips
                        .filter((tip) => typeof tip === 'string' && tip.trim())
                    : [];

                  if (stylistResponse?.success && (recommendedProducts.length || stylingTips.length)) {
                    await appendAgentMessage(
                      `👗 Our stylist just walked in with looks for your ${productDetails.name || 'new purchase'}!`,
                      {
                        metadata: {
                          stylist: {
                            stage: 'post_purchase',
                            product_sku: productDetails.sku || '',
                            recommendation_id: stylistResponse.recommendation_id || '',
                          },
                        },
                        messageProps: {
                          stylistRecommendations: {
                            purchasedProduct: stylistResponse.purchased_product || stylistPayload,
                            recommendedProducts,
                            stylingTips,
                            recommendationId: stylistResponse.recommendation_id || '',
                          },
                        },
                      }
                    );
                  }
                } catch (stylistError) {
                  console.error('Failed to fetch stylist suggestions:', stylistError);
                }
              }

              await appendAgentMessage(
                `Need any help after buying ${productDetails.name || 'this item'}? Choose a support option below.`,
                {
                  metadata: {
                    post_purchase: {
                      stage: 'cta',
                      order_id: orderId,
                      product_sku: productDetails.sku || '',
                      amount: parsedAmount,
                      address: recordedAddress,
                    },
                  },
                  messageProps: {
                    postPurchaseOptions: {
                      orderId,
                      productName: productDetails.name || '',
                      productSku: productDetails.sku || '',
                      amount: parsedAmount,
                      brand: productDetails.brand || '',
                      productCategory: productDetails.category || '',
                      productColor: productDetails.color || '',
                      productMaterial: productDetails.material || '',
                      productType: productDetails.productType || productDetails.category || '',
                      deliveryAddress: recordedAddress || undefined,
                    },
                  },
                }
              );
            }

            setPendingCheckoutItem(null);
            setAwaitingConfirmation(false);
          } catch (verifyError) {
            console.error('Payment verification failed:', verifyError);
            const failureText = `⚠️ Payment captured but verification failed. Please contact support. (${verifyError.message || 'Unknown error'})`;
            const failMessage = {
              id: Date.now() + Math.random(),
              text: failureText,
              sender: 'agent',
              timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
              status: 'read',
            };
            setMessages((prev) => [...prev, failMessage]);
            await saveChatMessage('agent', failureText);
          } finally {
            paymentInFlightRef.current = false;
            setIsPaymentProcessing(false);
          }
        },
      };

      const razorpayInstance = new window.Razorpay(options);
      razorpayInstance.on('payment.failed', async (failure) => {
        console.error('Razorpay payment failed:', failure);
        const failureText = `❌ Payment failed: ${failure.error?.description || 'Unknown error'}`;
        const failMessage = {
          id: Date.now() + Math.random(),
          text: failureText,
          sender: 'agent',
          timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          status: 'read',
        };
        setMessages((prev) => [...prev, failMessage]);
        await saveChatMessage('agent', failureText);
        paymentInFlightRef.current = false;
        setIsPaymentProcessing(false);
      });

      razorpayInstance.open();
    } catch (error) {
      console.error('Failed to initiate Razorpay payment:', error);
      const errorText = `❌ Unable to start Razorpay checkout: ${error.message || 'Unknown error'}`;
      const failMessage = {
        id: Date.now() + Math.random(),
        text: errorText,
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        status: 'read',
      };
      setMessages((prev) => [...prev, failMessage]);
      await saveChatMessage('agent', errorText);
      paymentInFlightRef.current = false;
      setIsPaymentProcessing(false);
    }
  };

  const handleProductPurchase = async (product) => {
    if (!sessionToken || !userId) {
      alert('Please start a chat session first.');
      return;
    }

    if (isPaymentProcessing) {
      return;
    }

    setIsPaymentProcessing(true);

    try {
      // Step 1: Calculate discounts
      const discountResponse = await fetch(`${API_ENDPOINTS.LOYALTY}/loyalty/calculate-discounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          cart_total: parseFloat(product.price)
        })
      });

      if (!discountResponse.ok) {
        throw new Error('Failed to calculate discounts');
      }

      const discountData = await discountResponse.json();

      // Step 2: Show discount breakdown to user
      const originalPrice = discountData.original_total;
      const finalPrice = discountData.final_total;
      const savings = originalPrice - finalPrice;

      const discountMessage = `🛒 **Purchase Summary**\n\n` +
        `📦 Product: ${product.name}\n` +
        `💰 Original Price: ₹${originalPrice}\n` +
        `${discountData.message}\n` +
        `💸 You Save: ₹${savings.toFixed(2)}\n` +
        `✅ Final Price: ₹${finalPrice.toFixed(2)}\n\n` +
        `🎁 Your Loyalty Status:\n` +
        `🏅 Tier: ${loyaltyTier}\n` +
        `💎 Points: ${loyaltyPoints}\n\n` +
        `Ready to proceed with payment?`;

      // Add discount summary message
      const discountMsg = {
        id: Date.now(),
        text: discountMessage,
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, discountMsg]);
      await saveChatMessage('agent', discountMessage);

      const payableAmount = parsePriceToNumber(finalPrice);
      const safeAmount = Number.isFinite(payableAmount) && payableAmount > 0
        ? payableAmount
        : parsePriceToNumber(product.price);

      if (!Number.isFinite(safeAmount) || safeAmount <= 0) {
        throw new Error('Unable to determine payable amount');
      }

      const normalizedQuantity = Number(product.quantity) > 0 ? Number(product.quantity) : 1;
      const orderId = buildCheckoutOrderId(product.sku || 'ITEM');
      const normalizedProduct = {
        ...product,
        price: safeAmount,
        rawPrice: product.price,
        quantity: normalizedQuantity,
        orderId,
      };

      setPendingCheckoutItem(normalizedProduct);

      await storeSelectedItemInSession({
        sku: normalizedProduct.sku,
        name: normalizedProduct.name,
        price: safeAmount,
        quantity: normalizedQuantity,
      });

      const checkoutPayload = {
        product: normalizedProduct,
        amount: safeAmount,
        orderId,
        quantity: normalizedQuantity,
      };

      setIsPaymentProcessing(false);

      const paymentPromptText = `Great! Your payable amount is ${formatINR(safeAmount)}. Tap "Please Pay Here" to add your delivery address and pay securely via Razorpay.`;
      const paymentPromptMessage = {
        id: Date.now() + Math.random(),
        text: paymentPromptText,
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        status: 'read',
        checkout: checkoutPayload,
      };

      setMessages((prev) => [...prev, paymentPromptMessage]);
      await saveChatMessage('agent', paymentPromptText, { checkout: checkoutPayload });

    } catch (error) {
      console.error('Purchase error:', error);
      alert('Failed to process purchase. Please try again.');
    } finally {
      setIsPaymentProcessing(false);
    }
  };

  const handlePaymentClick = async () => {
    // You can implement a generic payment action here if needed.
    // For now, it does nothing.
  };

  const sendMessageToAgent = async (messageText, { skipBackend = false } = {}) => {
    if (!messageText.trim() || !sessionToken) {
      return;
    }

    const messageId = Date.now();
    const timestamp = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    const userMessage = {
      id: messageId,
      text: messageText,
      sender: 'user',
      timestamp,
      status: skipBackend ? 'read' : 'sent',
    };

    setMessages((prev) => [...prev, userMessage]);
    await saveChatMessage('user', messageText);

    if (skipBackend) {
      return;
    }

    setTimeout(() => {
      setMessages((prev) => prev.map((msg) =>
        msg.id === messageId ? { ...msg, status: 'delivered' } : msg
      ));
    }, 500);

    setTimeout(() => {
      setMessages((prev) => prev.map((msg) =>
        msg.id === messageId ? { ...msg, status: 'read' } : msg
      ));
    }, 1000);

    setIsTyping(true);

    try {
      const payload = {
        message: messageText,
        session_token: sessionToken,
        metadata: { user_id: sessionInfo?.customer_id || sessionInfo?.phone }
      };

      const resp = await fetch(`${SALES_API}/api/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      setIsTyping(false);

      if (!resp.ok) {
        throw new Error('Agent error');
      }

      const data = await resp.json();
      const agentText = data.reply || 'Sorry, I could not process that.';

      if (data.session_token) {
        setSessionToken(data.session_token);
      }

      const agentMessage = {
        id: Date.now() + Math.random(),
        text: agentText,
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        status: 'read',
        cards: data.cards || [],
      };

      if (agentText.toLowerCase().includes('please confirm your cart')) {
        setAwaitingConfirmation(true);
      }

      setMessages((prev) => [...prev, agentMessage]);
      await saveChatMessage('agent', agentText, { cards: agentMessage.cards || [] });
    } catch (error) {
      setIsTyping(false);
      console.error('Agent call failed:', error);
      const failMsg = {
        id: Date.now() + Math.random(),
        text: 'Sorry, I could not reach the agent. Please try again later.',
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        status: 'read',
      };
      setMessages((prev) => [...prev, failMsg]);
      await saveChatMessage('agent', failMsg.text);
    }
  };

  const handleCheckoutConfirmation = async (messageText) => {
    await sendMessageToAgent(messageText, { skipBackend: true });

    if (!pendingCheckoutItem) {
      const infoText = 'I do not see any item in your cart yet. Please choose a product before confirming checkout.';
      const infoMessage = {
        id: Date.now() + Math.random(),
        text: infoText,
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        status: 'read',
      };
      setMessages((prev) => [...prev, infoMessage]);
      await saveChatMessage('agent', infoText);
      setAwaitingConfirmation(false);
      return;
    }

    const amount = parsePriceToNumber(pendingCheckoutItem.price ?? pendingCheckoutItem.rawPrice);
    if (!Number.isFinite(amount) || amount <= 0) {
      const warnText = 'Price information is missing for the selected item. Please ask the agent for the latest price before checking out.';
      const warnMessage = {
        id: Date.now() + Math.random(),
        text: warnText,
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        status: 'read',
      };
      setMessages((prev) => [...prev, warnMessage]);
      await saveChatMessage('agent', warnText);
      setAwaitingConfirmation(false);
      return;
    }

    const orderId = buildCheckoutOrderId(pendingCheckoutItem.sku || 'ITEM');
    const checkoutPayload = {
      product: { ...pendingCheckoutItem },
      amount,
      orderId,
      quantity: pendingCheckoutItem.quantity || 1,
    };

    setPendingCheckoutItem((prev) => (prev ? { ...prev, orderId } : prev));

    const agentText = `Great choice! Here's your checkout summary for ${pendingCheckoutItem.name || 'your selected product'}${pendingCheckoutItem.sku ? ` (SKU ${pendingCheckoutItem.sku})` : ''}. Total payable ${formatINR(amount)}. Tap "Please Pay Here" to finish the purchase.`;
    const checkoutMessage = {
      id: Date.now() + Math.random(),
      text: agentText,
      sender: 'agent',
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      status: 'read',
      checkout: checkoutPayload,
    };

    setMessages((prev) => [...prev, checkoutMessage]);
    await saveChatMessage('agent', agentText, { checkout: checkoutPayload });
    setAwaitingConfirmation(false);
  };

  const handleSendMessage = async () => {
    if (!sessionToken) {
      return;
    }

    const messageText = inputText.trim();
    if (!messageText) {
      return;
    }

    setInputText('');

    if (awaitingConfirmation && messageText.toLowerCase() === 'confirm') {
      await handleCheckoutConfirmation(messageText);
      return;
    }

    await sendMessageToAgent(messageText);
  };

  const handleCheckoutPayment = (checkout) => {
    if (!checkout) {
      return;
    }

    const amount = parsePriceToNumber(checkout.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      alert('Unable to determine payment amount. Please ask the agent for assistance.');
      return;
    }

    openAddressModalForPayment({
      amount,
      details: {
        orderId: checkout.orderId,
        sku: checkout.product?.sku,
        name: checkout.product?.name,
        source: 'guided-checkout',
        product: checkout.product,
      },
    });
  };

  const storeSelectedItemInSession = async (item) => {
    if (!sessionToken || !item) {
      return;
    }

    try {
      await fetch(`${SESSION_API}/session/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': sessionToken,
        },
        body: JSON.stringify({
          action: 'add_to_cart',
          payload: { item },
        }),
      });
    } catch (error) {
      console.error('Failed to persist cart item in session:', error);
    }
  };

  const handleBuyNow = async (card) => {
    if (!sessionToken) {
      alert('Start the chat session before selecting a product.');
      return;
    }

    const normalizedPrice = parsePriceToNumber(card.price);
    if (!Number.isFinite(normalizedPrice) || normalizedPrice <= 0) {
      alert('Price information is not available for this product yet. Please ask the agent for pricing details.');
      return;
    }

    const selection = {
      sku: card.sku || '',
      name: card.name || 'Selected product',
      price: normalizedPrice,
      rawPrice: card.price,
      image: card.image || '',
      brand: card.brand || '',
      category: card.category || extractCardAttribute(card, 'category') || '',
      color: extractCardAttribute(card, 'color') || card.color || '',
      material: extractCardAttribute(card, 'material') || '',
      productType: card.product_type || extractCardAttribute(card, 'product_type') || extractCardAttribute(card, 'type') || '',
      description: card.description || '',
      quantity: 1,
    };

    setPendingCheckoutItem(selection);
    setAwaitingConfirmation(false);

    await storeSelectedItemInSession({
      sku: selection.sku,
      name: selection.name,
      price: selection.price,
      quantity: selection.quantity,
    });

    const autoText = `I want to buy ${selection.name}${selection.sku ? ` (SKU ${selection.sku})` : ''}.`;
    await sendMessageToAgent(autoText);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const toggleVoiceRecording = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in your browser. Please use Chrome or Edge.');
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      transcriptRef.current = '';
      setInputText('');
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

  const getMessageStatusIcon = (status) => {
    switch(status) {
      case 'sent':
        return <Check className="w-4 h-4 text-gray-400" />;
      case 'delivered':
        return <CheckCheck className="w-4 h-4 text-gray-400" />;
      case 'read':
        return <CheckCheck className="w-4 h-4 text-blue-500" />;
      default:
        return null;
    }
  };

  const toggleExpandMessage = (id) => {
    setExpandedMessages(prev => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id); else s.add(id);
      return s;
    });
  };

  const toggleExpandCard = (id) => {
    setExpandedCards(prev => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id); else s.add(id);
      return s;
    });
  };

  const closeSupportPanel = () => {
    setShowSupportPanel(false);
    setActiveSupportMode(null);
    setSupportForm({});
    setSupportContext({});
    setSupportResult(null);
    setSupportError('');
    setPanelInitializing(false);
  };

  const openSupportPanel = async (mode, context = {}) => {
    if (!sessionToken) {
      alert('Start the chat session before using post-purchase services.');
      return;
    }

    setSupportResult(null);
    setSupportError('');
    setSupportContext(context || {});
    setShowSupportPanel(true);

    if (mode === 'menu') {
      setActiveSupportMode('menu');
      return;
    }

    setPanelInitializing(true);
    setActiveSupportMode(mode);

    // Detailed initialization logic will run below
    const baseUserId = sessionInfo?.data?.customer_id ? String(sessionInfo.data.customer_id) : (sessionInfo?.phone || '');
    const defaults = {
      user_id: baseUserId,
      order_id: context.orderId || context.order_id || lastCompletedOrder?.orderId || '',
      product_sku: context.productSku || context.product_sku || context.sku || lastCompletedOrder?.product?.sku || '',
      product_name: context.productName || context.product_name || lastCompletedOrder?.product?.name || '',
      category: context.productCategory || context.category || lastCompletedOrder?.product?.category || '',
      brand: context.brand || lastCompletedOrder?.product?.brand || '',
      color: context.productColor || context.color || lastCompletedOrder?.product?.color || '',
      material: context.productMaterial || context.material || lastCompletedOrder?.product?.material || '',
      product_type: context.productType || context.product_type || lastCompletedOrder?.product?.productType || lastCompletedOrder?.product?.category || '',
    };

    try {
      switch (mode) {
        case 'return': {
          let reasons = returnReasons;
          if (!reasons.length) {
            const reasonResp = await getReturnReasons();
            reasons = reasonResp.return_reasons || [];
            setReturnReasons(reasons);
          }
          setSupportForm({
            user_id: defaults.user_id,
            order_id: defaults.order_id,
            product_sku: defaults.product_sku,
            reason_code: (reasons[0]?.code || returnReasons[0]?.code) || '',
            additional_comments: '',
            images: '',
          });
          break;
        }
        case 'exchange': {
          setSupportForm({
            user_id: defaults.user_id,
            order_id: defaults.order_id,
            product_sku: defaults.product_sku,
            current_size: context.current_size || '',
            requested_size: '',
            reason: '',
          });
          break;
        }
        case 'complaint': {
          let issues = issueTypes;
          if (!issues.length) {
            const issueResp = await getIssueTypes();
            issues = issueResp.issue_types || [];
            setIssueTypes(issues);
          }
          setSupportForm({
            user_id: defaults.user_id,
            order_id: defaults.order_id,
            issue_type: issues[0] || '',
            description: '',
            priority: 'medium',
          });
          break;
        }
        case 'feedback': {
          setSupportForm({
            user_id: defaults.user_id,
            product_sku: defaults.product_sku,
            size_purchased: context.size_purchased || '',
            fit_rating: 'perfect',
            length_feedback: 'not_specified',
            comments: '',
          });
          break;
        }
        default: {
          setSupportForm(defaults);
        }
      }
    } catch (error) {
      console.error('Failed to prepare post-purchase panel:', error);
      setSupportError(error.message || 'Failed to load data for this action.');
    } finally {
      setPanelInitializing(false);
    }
  };


  // Phone Input Modal
  if (showPhoneInput) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#efeae2]">
        <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full mx-4">
          <div className="text-center mb-6">
            <div className="w-20 h-20 bg-[#25d366] rounded-full flex items-center justify-center mx-auto mb-4">
              <Phone className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-[#008069] mb-2">WhatsApp Chat</h2>
            <p className="text-gray-600">Enter your phone number to start or continue your session</p>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-[#25d366] focus:outline-none text-lg"
                onKeyPress={(e) => e.key === 'Enter' && !isLoadingSession && phoneNumber.trim() && startOrRestoreSession(phoneNumber)}
              />
            </div>
            
            <button
              onClick={() => startOrRestoreSession(phoneNumber)}
              disabled={isLoadingSession || !phoneNumber.trim()}
              className="w-full bg-[#25d366] text-white py-3 rounded-lg font-semibold hover:bg-[#20bd5a] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {isLoadingSession ? 'Connecting...' : 'Start Chat'}
            </button>
            
            <p className="text-xs text-gray-500 text-center">
              Your session stays active and is reusable across WhatsApp and Kiosk.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 bg-[#efeae2]">
      {/* Header - WhatsApp style */}
      <div className="bg-[#008069] text-white px-4 py-3 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-[#d9d9d9] flex items-center justify-center text-[#128c7e] font-semibold text-lg">
              AI
            </div>
            <div className="absolute bottom-0 right-0 w-3 h-3 bg-[#25d366] rounded-full border-2 border-[#008069]"></div>
          </div>
          <div>
            <h1 className="font-semibold text-base">AI Sales Agent</h1>
            <p className="text-xs text-[#d9d9d9]">online</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Loyalty Points & Tier Badge */}
          {loyaltyPoints > 0 && (
            <div className="flex items-center gap-2 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 px-3 py-1.5 rounded-full border border-yellow-500/50">
              <span className="text-xl">
                {loyaltyTier === 'Platinum' ? '💎' : loyaltyTier === 'Gold' ? '🥇' : loyaltyTier === 'Silver' ? '🥈' : '🥉'}
              </span>
              <div className="text-sm">
                <div className="flex items-center gap-1">
                  <span className="font-bold text-white">{loyaltyPoints}</span>
                  <span className="text-xs text-yellow-200">pts</span>
                </div>
                <div className="text-[10px] text-yellow-300 -mt-0.5 font-semibold">{loyaltyTier}</div>
              </div>
            </div>
          )}
          <button className="hover:bg-[#017561] p-2 rounded-full transition-colors">
            <Video className="w-5 h-5" />
          </button>
          <button
            onClick={() => openSupportPanel('menu')}
            className="hover:bg-[#017561] p-2 rounded-full transition-colors"
            title="Post-purchase support"
          >
            <LifeBuoy className="w-5 h-5" />
          </button>
          <button className="hover:bg-[#017561] p-2 rounded-full transition-colors">
            <Phone className="w-5 h-5" />
          </button>
          <button 
            onClick={endSession}
            className="hover:bg-[#c0392b] p-2 rounded-full transition-colors"
            title="End Session"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Session Continuity Banner */}
      {sessionInfo && (
        <div className="bg-gradient-to-r from-[#dcf8c6] to-[#d0f4de] border-b-2 border-[#25d366] px-4 py-3 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-[#25d366] rounded-full animate-pulse"></div>
              <div className="text-sm">
                <span className="font-semibold text-[#075e54]">Session Active:</span>
                <span className="ml-2 text-[#128c7e] font-mono text-xs">{sessionInfo.session_id}</span>
              </div>
            </div>
            <div className="flex items-center gap-4 text-xs text-[#075e54]">
              <div className="flex items-center gap-1">
                <User className="w-3 h-3" />
                <span className="font-medium">{sessionInfo.phone}</span>
              </div>
              <div className="px-2 py-1 bg-white/50 rounded-full">
                <span className="font-semibold">📱 WhatsApp</span>
              </div>
              {sessionInfo.data?.chat_context?.length > 1 && (
                <div className="text-[#00796b] font-medium">
                  ↻ Session restored ({sessionInfo.data.chat_context.length} messages)
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Chat Messages Area */}
      <div 
        className="flex-1 overflow-y-auto px-4 py-6 space-y-3 min-h-0"
        style={{
          backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'100\' height=\'100\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23d9d9d9\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M0 0h50v50H0zM50 50h50v50H50z\'/%3E%3C/g%3E%3C/svg%3E")',
        }}
      >
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] md:max-w-[65%] rounded-lg px-4 py-2 shadow-sm ${
                message.sender === 'user'
                  ? 'bg-[#d9fdd3] text-gray-900'
                  : 'bg-white text-gray-900'
              }`}
            >
              <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                {message.text && message.text.length > 800 && !expandedMessages.has(message.id)
                  ? `${message.text.slice(0, 380)}... `
                  : message.text}
                {message.text && message.text.length > 800 && (
                  <button
                    onClick={() => toggleExpandMessage(message.id)}
                    className="ml-1 text-xs text-[#00796b] font-medium hover:underline"
                  >
                    {expandedMessages.has(message.id) ? 'Show less' : 'Show more'}
                  </button>
                )}
              </div>
              
              {/* Product Cards */}
              {message.cards && message.cards.length > 0 && (
                <div className="mt-3 space-y-2">
                  {message.cards.map((card, idx) => (
                    <div key={idx} className="border border-gray-200 rounded-lg p-3 bg-gray-50 hover:bg-gray-100 transition-colors">
                      <div className="flex gap-3">
                        {card.image && (
                          <img 
                            src={card.image} 
                            alt={card.name} 
                            className="w-16 h-16 object-cover rounded"
                            onError={(e) => e.target.style.display = 'none'}
                          />
                        )}
                        <div className="flex-1">
                          <h4 className="font-semibold text-sm text-gray-900">{card.name}</h4>
                          <p className="text-xs text-gray-600 mt-1">{card.sku}</p>
                          {card.price && (
                            <p className="text-sm font-bold text-green-600 mt-1">₹{card.price}</p>
                          )}
                          {/* Show personalized reason AND gift message (if present). Fall back to description only if neither exists. */}
                          {(card.personalized_reason || card.gift_message || card.description) && (
                            <div className="mt-2 text-xs text-gray-500">
                              {/* Personalized reason (primary) */}
                              {card.personalized_reason && (
                                <div className="mb-2">
                                  {card.personalized_reason.length > 240 && !expandedCards.has(`${message.id}-${idx}-pr`)
                                    ? `${card.personalized_reason.slice(0, 220)}... `
                                    : card.personalized_reason}
                                  {card.personalized_reason.length > 240 && (
                                    <button
                                      onClick={() => toggleExpandCard(`${message.id}-${idx}-pr`)}
                                      className="ml-1 text-xs text-[#00796b] font-medium hover:underline"
                                    >
                                      {expandedCards.has(`${message.id}-${idx}-pr`) ? 'Show less' : 'Show more'}
                                    </button>
                                  )}
                                </div>
                              )}

                              {/* Gift message heading + message (italic, green, same size as description) */}
                              {card.gift_message && (
                                <div className="mb-2">
                                  <div className="text-xs font-medium text-[#075e54] mb-1">Gift message to attach:</div>
                                  <div className="italic text-xs text-[#0b6655]">
                                    {(() => {
                                      const gm = normalizeQuotes(card.gift_message);
                                      if (!gm) return null;
                                      const short = gm.length > 240 && !expandedCards.has(`${message.id}-${idx}-gift`);
                                      return (
                                        <>
                                          {short ? `"${gm.slice(0,220)}..." ` : `"${gm}"`}
                                          {gm.length > 240 && (
                                            <button
                                              onClick={() => toggleExpandCard(`${message.id}-${idx}-gift`)}
                                              className="ml-1 text-xs text-[#00796b] font-medium hover:underline"
                                            >
                                              {expandedCards.has(`${message.id}-${idx}-gift`) ? 'Show less' : 'Show more'}
                                            </button>
                                          )}
                                        </>
                                      );
                                    })()}
                                  </div>
                                </div>
                              )}

                              {/* If neither personalized nor gift message exist, show description with expand */}
                              {(!card.personalized_reason && !card.gift_message && card.description) && (
                                <>
                                  {card.description.length > 240 && !expandedCards.has(`${message.id}-${idx}`)
                                    ? `${card.description.slice(0, 220)}... `
                                    : card.description}
                                  {card.description.length > 240 && (
                                    <button
                                      onClick={() => toggleExpandCard(`${message.id}-${idx}`)}
                                      className="ml-1 text-xs text-[#00796b] font-medium hover:underline"
                                    >
                                      {expandedCards.has(`${message.id}-${idx}`) ? 'Show less' : 'Show more'}
                                    </button>
                                  )}
                                </>
                              )}

                              {/* Gift suitability tag */}
                              {card.gift_suitability && (
                                <div className="mt-1 inline-block bg-yellow-50 text-yellow-800 px-2 py-0.5 rounded-full text-[11px] font-medium">
                                  🎁 {card.gift_suitability}
                                </div>
                              )}
                            </div>
                          )}
                          
                          {/* Purchase Button */}
                          <div className="mt-3 flex justify-end">
                            <button
                              onClick={() => handleProductPurchase(card)}
                              disabled={isPaymentProcessing}
                              className="bg-[#00796b] hover:bg-[#00695c] disabled:bg-gray-400 text-white text-xs font-medium px-3 py-1.5 rounded-md transition-colors flex items-center gap-1"
                            >
                              <CreditCard className="w-3 h-3" />
                              {isPaymentProcessing ? 'Processing...' : 'Buy Now'}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {message.checkout && (
                <div className="mt-3 border border-green-200 bg-green-50 rounded-lg p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-green-700 mb-2">Checkout Summary</div>
                  <div className="text-sm text-gray-800 space-y-1">
                    <div className="font-medium">{message.checkout.product?.name || 'Selected product'}</div>
                    {message.checkout.product?.sku && (
                      <div className="text-xs text-gray-600">SKU: {message.checkout.product.sku}</div>
                    )}
                    <div className="text-sm font-semibold text-green-700">
                      Total: {formatINR(message.checkout.amount)}
                    </div>
                    {message.checkout.orderId && (
                      <div className="text-xs text-gray-600">Order ID: {message.checkout.orderId}</div>
                    )}
                  </div>
                  <button
                    onClick={() => handleCheckoutPayment(message.checkout)}
                    className="mt-3 inline-flex items-center justify-center gap-2 w-full px-3 py-2 bg-[#128c7e] text-white text-sm font-semibold rounded-lg hover:bg-[#0a6258] transition-colors disabled:cursor-not-allowed disabled:opacity-70"
                    disabled={isPaymentProcessing}
                  >
                    <CreditCard className="w-4 h-4" />
                    <span>Please Pay Here</span>
                  </button>
                  {isPaymentProcessing && (
                    <p className="mt-2 text-xs text-[#075e54]">Opening Razorpay checkout...</p>
                  )}
                </div>
              )}

              {message.stylistRecommendations && (
                <div className="mt-3 border border-indigo-200 bg-indigo-50 rounded-lg p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Stylist Picks</div>
                  <p className="text-sm text-indigo-900 mt-1">
                    {message.stylistRecommendations.purchasedProduct?.name
                      ? `Ideas to style your ${message.stylistRecommendations.purchasedProduct.name}.`
                      : 'Ideas to style your new purchase.'}
                  </p>

                  {message.stylistRecommendations.recommendedProducts?.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {message.stylistRecommendations.recommendedProducts.map((item, idx) => (
                        <div key={`${message.id}-stylist-${idx}`} className="bg-white border border-indigo-100 rounded-lg p-3 shadow-sm">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="text-sm font-semibold text-indigo-900">
                                {item.name || `Recommendation ${idx + 1}`}
                              </div>
                              {item.sku && (
                                <div className="text-xs text-indigo-700 mt-1">SKU: {item.sku}</div>
                              )}
                            </div>
                          </div>
                          {item.reason && (
                            <p className="text-xs text-indigo-800 mt-2 leading-snug">
                              {item.reason}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {message.stylistRecommendations.stylingTips?.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-semibold text-indigo-800 uppercase tracking-wide">Styling Tips</div>
                      <ul className="mt-2 list-disc list-inside text-xs text-indigo-900 space-y-1">
                        {message.stylistRecommendations.stylingTips.map((tip, idx) => (
                          <li key={`${message.id}-stylist-tip-${idx}`}>{tip}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {message.postPurchaseOptions && (
                <div className="mt-3 border border-emerald-200 bg-emerald-50 rounded-lg p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Post-Purchase Support</div>
                  <p className="text-sm text-emerald-900 mt-1">
                    {message.postPurchaseOptions.productName
                      ? `Need help with ${message.postPurchaseOptions.productName}? Choose an option below.`
                      : 'Need help after your purchase? Pick an option below.'}
                  </p>
                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {supportActions.map((action) => (
                      <button
                        key={action.key}
                        type="button"
                        onClick={() => openSupportPanel(action.key, message.postPurchaseOptions)}
                        className="text-left px-3 py-2 bg-white border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors"
                      >
                        <div className="text-sm font-semibold text-emerald-800">{`${action.emoji} ${action.label}`}</div>
                        <div className="text-xs text-emerald-700 mt-1">{action.caption}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              
              <div className={`flex items-center gap-1 justify-end mt-1 ${
                message.sender === 'user' ? 'text-gray-600' : 'text-gray-500'
              }`}>
                <span className="text-[10px]">{message.timestamp}</span>
                {message.sender === 'user' && getMessageStatusIcon(message.status)}
              </div>
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white rounded-lg px-4 py-3 shadow-sm">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area - WhatsApp style */}
      <div className="bg-[#f0f2f5] px-4 py-3 border-t border-gray-200">
        <div className="flex items-end gap-2">
          <div className="flex-1 bg-white rounded-full px-4 py-2 flex items-center gap-2 shadow-sm">
            <button className="text-gray-500 hover:text-gray-700">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9.153 11.603c.795 0 1.439-.879 1.439-1.962s-.644-1.962-1.439-1.962-1.439.879-1.439 1.962.644 1.962 1.439 1.962zm-3.204 1.362c-.026-.307-.131 5.218 6.063 5.551 6.066-.25 6.066-5.551 6.066-5.551-6.078 1.416-12.129 0-12.129 0zm11.363 1.108s-.669 1.959-5.051 1.959c-3.505 0-5.388-1.164-5.607-1.959 0 0 5.912 1.055 10.658 0zM11.804 1.011C5.609 1.011.978 6.033.978 12.228s4.826 10.761 11.021 10.761S23.02 18.423 23.02 12.228c.001-6.195-5.021-11.217-11.216-11.217zM12 21.354c-5.273 0-9.381-3.886-9.381-9.159s3.942-9.548 9.215-9.548 9.548 4.275 9.548 9.548c-.001 5.272-4.109 9.159-9.382 9.159zm3.108-9.751c.795 0 1.439-.879 1.439-1.962s-.644-1.962-1.439-1.962-1.439.879-1.439 1.962.644 1.962 1.439 1.962z"/>
              </svg>
            </button>
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type a message"
              className="flex-1 bg-transparent outline-none text-sm placeholder:text-gray-500"
            />
            <button
              onClick={handlePaymentClick}
              disabled={!sessionToken || !isRazorpayReady || isPaymentProcessing}
              className={`transition-colors ${(!sessionToken || !isRazorpayReady || isPaymentProcessing) ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:text-gray-700'}`}
              title={isPaymentProcessing ? 'Processing payment...' : 'Collect payment via Razorpay'}
            >
              <CreditCard className="w-6 h-6" />
            </button>
            <button 
              onClick={toggleVoiceRecording}
              className={`transition-colors ${
                isRecording 
                  ? 'text-red-500 hover:text-red-700 animate-pulse' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title={isRecording ? 'Stop recording' : 'Start voice input'}
            >
              {isRecording ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
            </button>
          </div>
          <button
            onClick={handleSendMessage}
            disabled={!inputText.trim()}
            className={`rounded-full p-3 transition-all ${
              inputText.trim()
                ? 'bg-[#008069] hover:bg-[#017561] text-white'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>

      {showAddressModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 px-4 py-6">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Add Delivery Address</h2>
                {pendingPaymentDetails?.details?.name && (
                  <p className="text-xs text-gray-500 mt-1">
                    For {pendingPaymentDetails.details.name}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={closeAddressModal}
                className="p-2 rounded-full hover:bg-gray-100 text-gray-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={submitAddressForm} className="px-6 py-4 space-y-4">
              {addressError && (
                <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {addressError}
                </div>
              )}
              <label className="block text-xs font-medium text-gray-600 uppercase">
                City
                <input
                  type="text"
                  value={addressForm.city}
                  onChange={(e) => handleAddressInputChange('city', e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                  required
                  placeholder="e.g., Mumbai"
                />
              </label>
              <label className="block text-xs font-medium text-gray-600 uppercase">
                Landmark
                <input
                  type="text"
                  value={addressForm.landmark}
                  onChange={(e) => handleAddressInputChange('landmark', e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                  required
                  placeholder="e.g., Near City Mall"
                />
              </label>
              <label className="block text-xs font-medium text-gray-600 uppercase">
                Building / House Name
                <input
                  type="text"
                  value={addressForm.building}
                  onChange={(e) => handleAddressInputChange('building', e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                  required
                  placeholder="e.g., Sunrise Apartments"
                />
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={closeAddressModal}
                  className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-semibold text-white bg-[#128c7e] rounded-lg hover:bg-[#0a6258] transition-colors disabled:cursor-not-allowed disabled:opacity-70"
                  disabled={isPaymentProcessing}
                >
                  {isPaymentProcessing ? 'Processing...' : 'Continue to Payment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showSupportPanel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6">
          <div className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {SUPPORT_TITLES[activeSupportMode] || SUPPORT_TITLES.menu}
                </h2>
                {activeSupportMode && activeSupportMode !== 'menu' && (supportContext.productName || lastCompletedOrder?.product?.name) && (
                  <p className="text-xs text-gray-500 mt-1">
                    For {supportContext.productName || lastCompletedOrder?.product?.name}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {activeSupportMode !== 'menu' && (
                  <button
                    type="button"
                    onClick={() => openSupportPanel('menu', supportContext)}
                    className="px-3 py-1 text-xs font-medium text-emerald-700 border border-emerald-200 rounded-full hover:bg-emerald-50"
                  >
                    All options
                  </button>
                )}
                <button
                  type="button"
                  onClick={closeSupportPanel}
                  className="p-2 rounded-full hover:bg-gray-100 text-gray-500"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="px-6 py-4 max-h-[70vh] overflow-y-auto">
              {panelInitializing ? (
                <p className="py-6 text-center text-sm text-gray-500">Loading details...</p>
              ) : activeSupportMode === 'menu' ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {supportActions.map((action) => (
                    <button
                      key={action.key}
                      type="button"
                      onClick={() => openSupportPanel(action.key, supportContext)}
                      className="text-left px-3 py-3 bg-emerald-50 border border-emerald-100 rounded-xl hover:bg-emerald-100 transition-colors"
                    >
                      <div className="text-sm font-semibold text-emerald-800">{`${action.emoji} ${action.label}`}</div>
                      <div className="text-xs text-emerald-700 mt-1">{action.caption}</div>
                    </button>
                  ))}
                </div>
              ) : (
                <form onSubmit={submitSupportForm} className="space-y-4">
                  {supportError && (
                    <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
                      {supportError}
                    </div>
                  )}

                  {activeSupportMode === 'return' && (
                    <div className="grid gap-3">
                      <label className="block text-xs font-medium text-gray-600 uppercase">User ID
                        <input
                          type="text"
                          value={supportForm.user_id || ''}
                          readOnly
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-gray-100"
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Order ID
                        <input
                          type="text"
                          value={supportForm.order_id || ''}
                          onChange={(e) => updateSupportForm('order_id', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          required
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Product SKU
                        <input
                          type="text"
                          value={supportForm.product_sku || ''}
                          onChange={(e) => updateSupportForm('product_sku', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          required
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Return Reason
                        <select
                          value={supportForm.reason_code || ''}
                          onChange={(e) => updateSupportForm('reason_code', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          required
                        >
                          <option value="" disabled>Select reason</option>
                          {(returnReasons.length ? returnReasons : [{ code: supportForm.reason_code, label: supportForm.reason_code }]).map((reason) => (
                            <option key={reason.code} value={reason.code}>
                              {reason.label || reason.code}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Additional Comments
                        <textarea
                          value={supportForm.additional_comments || ''}
                          onChange={(e) => updateSupportForm('additional_comments', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          rows={3}
                          placeholder="Share any details for the pickup team"
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Image URLs (optional)
                        <textarea
                          value={supportForm.images || ''}
                          onChange={(e) => updateSupportForm('images', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          rows={2}
                          placeholder="Comma separated URLs"
                        />
                      </label>
                    </div>
                  )}

                  {activeSupportMode === 'exchange' && (
                    <div className="grid gap-3">
                      <label className="block text-xs font-medium text-gray-600 uppercase">User ID
                        <input
                          type="text"
                          value={supportForm.user_id || ''}
                          readOnly
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-gray-100"
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Order ID
                        <input
                          type="text"
                          value={supportForm.order_id || ''}
                          onChange={(e) => updateSupportForm('order_id', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          required
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Product SKU
                        <input
                          type="text"
                          value={supportForm.product_sku || ''}
                          onChange={(e) => updateSupportForm('product_sku', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          required
                        />
                      </label>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <label className="block text-xs font-medium text-gray-600 uppercase">Current Size
                          <input
                            type="text"
                            value={supportForm.current_size || ''}
                            onChange={(e) => updateSupportForm('current_size', e.target.value)}
                            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          />
                        </label>
                        <label className="block text-xs font-medium text-gray-600 uppercase">Requested Size
                          <input
                            type="text"
                            value={supportForm.requested_size || ''}
                            onChange={(e) => updateSupportForm('requested_size', e.target.value)}
                            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                            required
                          />
                        </label>
                      </div>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Reason (optional)
                        <textarea
                          value={supportForm.reason || ''}
                          onChange={(e) => updateSupportForm('reason', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          rows={2}
                        />
                      </label>
                    </div>
                  )}

                  {activeSupportMode === 'complaint' && (
                    <div className="grid gap-3">
                      <label className="block text-xs font-medium text-gray-600 uppercase">User ID
                        <input
                          type="text"
                          value={supportForm.user_id || ''}
                          readOnly
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-gray-100"
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Order ID (optional)
                        <input
                          type="text"
                          value={supportForm.order_id || ''}
                          onChange={(e) => updateSupportForm('order_id', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Issue Type
                        <select
                          value={supportForm.issue_type || ''}
                          onChange={(e) => updateSupportForm('issue_type', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          required
                        >
                          <option value="" disabled>Select issue</option>
                          {(issueTypes.length ? issueTypes : [supportForm.issue_type]).map((issue) => (
                            <option key={issue} value={issue}>
                              {issue}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Priority
                        <select
                          value={supportForm.priority || 'medium'}
                          onChange={(e) => updateSupportForm('priority', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                        >
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
                        </select>
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Description
                        <textarea
                          value={supportForm.description || ''}
                          onChange={(e) => updateSupportForm('description', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          rows={3}
                          required
                        />
                      </label>
                    </div>
                  )}


                  {activeSupportMode === 'feedback' && (
                    <div className="grid gap-3">
                      <label className="block text-xs font-medium text-gray-600 uppercase">User ID
                        <input
                          type="text"
                          value={supportForm.user_id || ''}
                          readOnly
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-gray-100"
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Product SKU
                        <input
                          type="text"
                          value={supportForm.product_sku || ''}
                          onChange={(e) => updateSupportForm('product_sku', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          required
                        />
                      </label>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Size Purchased
                        <input
                          type="text"
                          value={supportForm.size_purchased || ''}
                          onChange={(e) => updateSupportForm('size_purchased', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          required
                        />
                      </label>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <label className="block text-xs font-medium text-gray-600 uppercase">Fit Rating
                          <select
                            value={supportForm.fit_rating || 'perfect'}
                            onChange={(e) => updateSupportForm('fit_rating', e.target.value)}
                            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          >
                            <option value="too_tight">Too tight</option>
                            <option value="perfect">Perfect</option>
                            <option value="too_loose">Too loose</option>
                          </select>
                        </label>
                        <label className="block text-xs font-medium text-gray-600 uppercase">Length Feedback
                          <select
                            value={supportForm.length_feedback || 'not_specified'}
                            onChange={(e) => updateSupportForm('length_feedback', e.target.value)}
                            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          >
                            <option value="not_specified">Not specified</option>
                            <option value="too_short">Too short</option>
                            <option value="perfect">Perfect</option>
                            <option value="too_long">Too long</option>
                          </select>
                        </label>
                      </div>
                      <label className="block text-xs font-medium text-gray-600 uppercase">Comments (optional)
                        <textarea
                          value={supportForm.comments || ''}
                          onChange={(e) => updateSupportForm('comments', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                          rows={3}
                        />
                      </label>
                    </div>
                  )}

                  {supportResult && supportResult.type === activeSupportMode && supportResult.summary && (
                    <div className="rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm text-emerald-800 whitespace-pre-wrap">
                      {supportResult.summary}
                    </div>
                  )}

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={closeSupportPanel}
                      className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50"
                    >
                      Close
                    </button>
                    <button
                      type="submit"
                      disabled={supportLoading}
                      className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-60"
                    >
                      {supportLoading ? 'Submitting...' : 'Submit'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chat;
