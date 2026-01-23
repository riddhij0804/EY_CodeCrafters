// Main service index - Exports all services for easy import

export { default as inventoryService } from './inventoryService';
export { default as loyaltyService } from './loyaltyService';
export { default as paymentService } from './paymentService';
export { default as postPurchaseService } from './postPurchaseService';
export { default as fulfillmentService } from './fulfillmentService';
export { default as dataService } from './dataService';
export { default as salesAgentService } from './salesAgentService';

// Re-export individual functions for direct access
export * from './inventoryService';
export * from './loyaltyService';
export * from './paymentService';
export * from './postPurchaseService';
export * from './fulfillmentService';
export * from './salesAgentService';
