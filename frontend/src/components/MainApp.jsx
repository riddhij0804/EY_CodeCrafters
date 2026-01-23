import React, { useState, useRef } from 'react';
import { MessageCircle, Users } from 'lucide-react';
import Chat from './Chat';
import Community from './Community';

/**
 * Main Application with Tabs
 * - Chat: 1-to-1 AI Assistant (existing)
 * - Community: Virtual Circles (new)
 * 
 * Frontend NEVER calls Virtual Circles Agent directly
 * Flow: Frontend → Sales Agent → Virtual Circles Agent
 */
const MainApp = () => {
  const [activeTab, setActiveTab] = useState('chat');
  const communityRef = useRef();

  const handleCommunityClick = () => {
    setActiveTab('community');
    // Trigger session initialization when community tab is opened
    // This ensures the session is created/restored when user wants to join
    if (communityRef.current?.initializeSession) {
      communityRef.current.initializeSession();
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Tab Navigation */}
      <div className="bg-white border-b shadow-sm">
        <div className="flex items-center justify-center space-x-1 px-6 py-2">
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === 'chat'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <MessageCircle className="w-5 h-5" />
            <span>Chat</span>
          </button>
          
          <button
            onClick={handleCommunityClick}
            className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === 'community'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Users className="w-5 h-5" />
            <span>Join Community</span>
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chat' ? <Chat /> : <Community ref={communityRef} />}
      </div>
    </div>
  );
};

export default MainApp;
