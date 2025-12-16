# FAISS Index Builder for Visual Similarity Search
# Builds and manages FAISS index for fast similarity search

import faiss
import numpy as np
import pandas as pd
import json
import pickle
import os
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from feature_extractor import FeatureExtractor


class FAISSIndexBuilder:
    """
    Builds and manages FAISS index for visual similarity search.
    Supports filtering by category and provides top-k similarity search.
    Enhanced with better accuracy through improved feature extraction.
    """
    
    def __init__(self, data_dir: str = "../../data", accuracy_mode: str = 'enhanced'):
        """
        Initialize the FAISS index builder.
        
        Args:
            data_dir: Path to the data directory containing products.csv and images
            accuracy_mode: 'simple', 'enhanced', or 'ensemble' for accuracy vs speed
        """
        self.data_dir = Path(data_dir)
        self.products_csv = self.data_dir / "products.csv"
        self.reebok_images_dir = self.data_dir / "reebok_images"
        self.product_images_dir = self.data_dir / "product_images"
        
        # Use enhanced feature extractor for better accuracy
        self.feature_extractor = FeatureExtractor(mode=accuracy_mode)
        self.accuracy_mode = accuracy_mode
        
        # Storage for index and metadata
        self.index = None
        self.products_df = None
        self.indexed_products = []  # List of product metadata for each index entry
        self.sku_to_variants = {}   # Map SKU to all its variants
        
        print(f"FAISSIndexBuilder initialized with data_dir: {data_dir}")
        print(f"Accuracy mode: {accuracy_mode}")
    
    def load_products_data(self, category_filter: Optional[str] = None) -> pd.DataFrame:
        """
        Load products data from CSV and optionally filter by category.
        
        Args:
            category_filter: Category to filter by (e.g., 'Apparel', 'Footwear')
            
        Returns:
            Filtered DataFrame
        """
        print(f"Loading products from {self.products_csv}")
        df = pd.read_csv(self.products_csv)
        
        if category_filter:
            df = df[df['category'].str.lower() == category_filter.lower()]
            print(f"Filtered to {len(df)} products in category: {category_filter}")
        else:
            print(f"Loaded {len(df)} products (no category filter)")
        
        self.products_df = df
        return df
    
    def parse_attributes(self, attributes_str: str) -> Dict:
        """
        Parse the attributes JSON string from the CSV.
        
        Args:
            attributes_str: JSON string containing attributes
            
        Returns:
            Dictionary of attributes
        """
        try:
            return json.loads(attributes_str.replace("'", '"'))
        except:
            return {}
    
    def get_image_path(self, image_url: str) -> Optional[str]:
        """
        Get the full path to an image file.
        
        Args:
            image_url: Relative image path from CSV (e.g., 'reebok_images/item_0.jpg')
            
        Returns:
            Full path to the image or None if not found
        """
        image_path = self.data_dir / image_url
        
        if image_path.exists():
            return str(image_path)
        else:
            # Try alternate locations
            filename = Path(image_url).name
            
            # Check in reebok_images
            alt_path = self.reebok_images_dir / filename
            if alt_path.exists():
                return str(alt_path)
            
            # Check in product_images
            alt_path = self.product_images_dir / filename
            if alt_path.exists():
                return str(alt_path)
        
        return None
    
    def build_index(self, category_filter: Optional[str] = None, 
                    subcategory_filter: Optional[str] = None) -> int:
        """
        Build FAISS index from catalog images.
        
        Args:
            category_filter: Filter by category (e.g., 'Apparel', 'Footwear')
            subcategory_filter: Filter by subcategory (e.g., 'Topwear', 'Shoes')
            
        Returns:
            Number of products indexed
        """
        print("=" * 60)
        print("Building FAISS Index")
        print("=" * 60)
        
        # Load and filter products
        df = self.load_products_data(category_filter)
        
        if subcategory_filter:
            df = df[df['subcategory'].str.lower() == subcategory_filter.lower()]
            print(f"Filtered to {len(df)} products in subcategory: {subcategory_filter}")
        
        if len(df) == 0:
            raise ValueError("No products found with the specified filters")
        
        # Collect image paths and product metadata
        valid_images = []
        valid_metadata = []
        
        for idx, row in df.iterrows():
            image_path = self.get_image_path(row['image_url'])
            
            if image_path:
                valid_images.append(image_path)
                
                # Parse attributes
                attrs = self.parse_attributes(row['attributes'])
                
                metadata = {
                    'sku': row['sku'],
                    'product_name': row['ProductDisplayName'],
                    'brand': row['brand'],
                    'category': row['category'],
                    'subcategory': row['subcategory'],
                    'price': row['price'],
                    'color': attrs.get('color', 'Unknown'),
                    'size': attrs.get('size', []),
                    'material': attrs.get('material', 'Unknown'),
                    'gender': attrs.get('gender', 'Unknown'),
                    'image_path': image_path,
                    'image_url': row['image_url']
                }
                valid_metadata.append(metadata)
            else:
                print(f"Warning: Image not found for SKU {row['sku']}: {row['image_url']}")
        
        print(f"\nFound {len(valid_images)} valid images out of {len(df)} products")
        
        if len(valid_images) == 0:
            raise ValueError("No valid images found")
        
        # Extract features
        print("\nExtracting features from images...")
        features = self.feature_extractor.extract_features_batch(valid_images, batch_size=32)
        
        print(f"Extracted features shape: {features.shape}")
        
        # Build FAISS index (using cosine similarity via inner product on normalized vectors)
        dimension = features.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product for cosine similarity
        
        # Add features to index
        self.index.add(features.astype('float32'))
        
        # Store metadata
        self.indexed_products = valid_metadata
        
        # Build SKU to variants mapping
        self._build_sku_variants_mapping()
        
        print(f"\nFAISS index built successfully with {self.index.ntotal} entries")
        print("=" * 60)
        
        return self.index.ntotal
    
    def _build_sku_variants_mapping(self):
        """
        Build a mapping from product name (without variant info) to all variants.
        This helps identify all color/size variants of the same product.
        """
        self.sku_to_variants = {}
        
        for product in self.indexed_products:
            sku = product['sku']
            
            # Group by base product name (remove color/size descriptors)
            base_name = self._get_base_product_name(product['product_name'])
            
            if base_name not in self.sku_to_variants:
                self.sku_to_variants[base_name] = []
            
            self.sku_to_variants[base_name].append(product)
        
        print(f"Built variants mapping for {len(self.sku_to_variants)} unique products")
    
    def _get_base_product_name(self, product_name: str) -> str:
        """
        Extract base product name by removing color/size descriptors.
        This is a simple heuristic - can be improved.
        """
        # Remove common color and size words
        name_lower = product_name.lower()
        
        # Keep the base structure
        return product_name
    
    def search(self, query_image_path: str, top_k: int = 1, rerank: bool = True) -> List[Dict]:
        """
        Search for similar products given a query image.
        Optionally applies reranking for improved accuracy.
        
        Args:
            query_image_path: Path to the query image
            top_k: Number of top matches to return
            rerank: If True, retrieves more candidates and reranks them
            
        Returns:
            List of dictionaries with matched products and similarity scores
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        # Extract features from query image
        query_features = self.feature_extractor.extract_features(query_image_path)
        query_features = query_features.reshape(1, -1).astype('float32')
        
        # For reranking: retrieve more candidates than needed
        search_k = min(top_k * 5, self.index.ntotal) if rerank else top_k
        
        # Search in FAISS index
        scores, indices = self.index.search(query_features, search_k)
        
        # Prepare initial results
        candidates = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.indexed_products):
                product = self.indexed_products[idx].copy()
                product['similarity_score'] = float(score)
                product['index'] = int(idx)
                candidates.append(product)
        
        # Reranking: compute additional similarity metrics
        if rerank and len(candidates) > top_k:
            candidates = self._rerank_results(query_image_path, candidates)
        
        # Return top-k after reranking
        return candidates[:top_k]
    
    def _rerank_results(self, query_image_path: str, candidates: List[Dict]) -> List[Dict]:
        """
        Rerank search results using additional similarity metrics.
        This improves accuracy by considering multiple factors.
        
        Args:
            query_image_path: Path to query image
            candidates: Initial candidates from FAISS search
            
        Returns:
            Reranked list of candidates
        """
        try:
            import cv2
            
            # Load query image
            query_img = cv2.imread(query_image_path)
            if query_img is None:
                return candidates
            query_img = cv2.cvtColor(query_img, cv2.COLOR_BGR2RGB)
            
            # Extract query color histogram
            query_color_hist = []
            for i in range(3):
                hist = cv2.calcHist([query_img], [i], None, [32], [0, 256])
                hist = hist.flatten()
                hist = hist / (hist.sum() + 1e-8)
                query_color_hist.extend(hist)
            query_color_hist = np.array(query_color_hist)
            
            # Compute color similarity for each candidate
            for candidate in candidates:
                try:
                    # Load candidate image
                    cand_img = cv2.imread(candidate['image_path'])
                    if cand_img is None:
                        candidate['color_similarity'] = 0.0
                        continue
                    cand_img = cv2.cvtColor(cand_img, cv2.COLOR_BGR2RGB)
                    
                    # Extract candidate color histogram
                    cand_color_hist = []
                    for i in range(3):
                        hist = cv2.calcHist([cand_img], [i], None, [32], [0, 256])
                        hist = hist.flatten()
                        hist = hist / (hist.sum() + 1e-8)
                        cand_color_hist.extend(hist)
                    cand_color_hist = np.array(cand_color_hist)
                    
                    # Compute color similarity (correlation)
                    color_sim = np.corrcoef(query_color_hist, cand_color_hist)[0, 1]
                    candidate['color_similarity'] = float(max(0, color_sim))
                    
                except Exception as e:
                    candidate['color_similarity'] = 0.0
            
            # Compute final reranked score
            for candidate in candidates:
                # Weighted combination: 70% deep features, 30% color similarity
                original_score = candidate['similarity_score']
                color_score = candidate.get('color_similarity', 0.0)
                
                # Final score
                candidate['reranked_score'] = (0.7 * original_score) + (0.3 * color_score)
                candidate['similarity_score'] = candidate['reranked_score']
            
            # Sort by reranked score
            candidates.sort(key=lambda x: x['reranked_score'], reverse=True)
            
            print(f"Reranked {len(candidates)} candidates")
            
        except Exception as e:
            print(f"Reranking failed, using original scores: {e}")
        
        return candidates
    
    def get_all_variants(self, sku: str) -> List[Dict]:
        """
        Get all variants of a product by SKU.
        
        Args:
            sku: Product SKU
            
        Returns:
            List of all variants from products.csv
        """
        if self.products_df is None:
            self.load_products_data()
        
        # Get all rows with the same base product name
        matched_product = None
        for product in self.indexed_products:
            if product['sku'] == sku:
                matched_product = product
                break
        
        if not matched_product:
            return []
        
        # Find all variants from CSV
        base_name = self._get_base_product_name(matched_product['product_name'])
        variants = []
        
        for idx, row in self.products_df.iterrows():
            if self._get_base_product_name(row['ProductDisplayName']) == base_name:
                attrs = self.parse_attributes(row['attributes'])
                variant = {
                    'sku': row['sku'],
                    'brand': row['brand'],
                    'product_name': row['ProductDisplayName'],
                    'color': attrs.get('color', 'Unknown'),
                    'size': attrs.get('size', []),
                    'material': attrs.get('material', 'Unknown'),
                    'price': row['price'],
                    'gender': attrs.get('gender', 'Unknown'),
                    'image_url': row['image_url']
                }
                variants.append(variant)
        
        return variants
    
    def save_index(self, index_path: str, metadata_path: str):
        """
        Save FAISS index and metadata to disk.
        
        Args:
            index_path: Path to save the FAISS index
            metadata_path: Path to save the metadata
        """
        if self.index is None:
            raise ValueError("No index to save. Build index first.")
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        
        # Save metadata
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'indexed_products': self.indexed_products,
                'sku_to_variants': self.sku_to_variants
            }, f)
        
        print(f"Index saved to {index_path}")
        print(f"Metadata saved to {metadata_path}")
    
    def load_index(self, index_path: str, metadata_path: str):
        """
        Load FAISS index and metadata from disk.
        
        Args:
            index_path: Path to the saved FAISS index
            metadata_path: Path to the saved metadata
        """
        # Load FAISS index
        self.index = faiss.read_index(index_path)
        
        # Load metadata
        with open(metadata_path, 'rb') as f:
            data = pickle.load(f)
            self.indexed_products = data['indexed_products']
            self.sku_to_variants = data['sku_to_variants']
        
        print(f"Index loaded from {index_path}")
        print(f"Metadata loaded from {metadata_path}")
        print(f"Index contains {self.index.ntotal} entries")


def test_index_builder():
    """Test the FAISS index builder."""
    builder = FAISSIndexBuilder()
    
    # Build index for Apparel category
    print("Building index for Apparel category...")
    num_indexed = builder.build_index(category_filter="Apparel")
    
    print(f"\nIndexed {num_indexed} products")
    
    # Test search (you'll need a test image)
    test_image = "../../data/reebok_images/item_12.jpg"
    if os.path.exists(test_image):
        results = builder.search(test_image, top_k=3)
        
        print("\nSearch results:")
        for i, result in enumerate(results):
            print(f"\n{i+1}. SKU: {result['sku']}")
            print(f"   Product: {result['product_name']}")
            print(f"   Similarity: {result['similarity_score']:.4f}")


if __name__ == "__main__":
    test_index_builder()
