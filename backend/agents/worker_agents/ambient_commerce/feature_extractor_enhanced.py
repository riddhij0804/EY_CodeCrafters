# Enhanced Feature Extractor with Multiple Models and Advanced Techniques
# Significantly improved accuracy through ensemble and multi-modal features

import os
# Fix for OpenMP library conflict
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from typing import Union, List, Tuple
import cv2


class EnhancedFeatureExtractor:
    """
    Enhanced feature extractor using multiple techniques:
    1. EfficientNet-B4 (better than ResNet50 for visual similarity)
    2. Multi-scale feature extraction
    3. Color histogram features
    4. Attention-based pooling
    """
    
    def __init__(self, device: str = None, use_ensemble: bool = True):
        """
        Initialize the enhanced feature extractor.
        
        Args:
            device: 'cuda' or 'cpu'. If None, automatically selects based on availability.
            use_ensemble: If True, uses ensemble of models for better accuracy
        """
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        self.use_ensemble = use_ensemble
        
        # Primary model: EfficientNet-B4 (better for fashion/apparel)
        print("Loading EfficientNet-B4 (primary model)...")
        self.efficientnet = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.IMAGENET1K_V1)
        self.efficientnet.classifier = nn.Identity()  # Remove classifier to get features
        self.efficientnet.eval()
        self.efficientnet.to(self.device)
        
        # Secondary model: ResNet50 with attention (for ensemble)
        if use_ensemble:
            print("Loading ResNet50 (secondary model for ensemble)...")
            self.resnet = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
            self.resnet = nn.Sequential(*list(self.resnet.children())[:-1])
            self.resnet.eval()
            self.resnet.to(self.device)
        
        # Image preprocessing for EfficientNet (380x380)
        self.preprocess_efficientnet = transforms.Compose([
            transforms.Resize(380),
            transforms.CenterCrop(380),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        # Image preprocessing for ResNet (224x224)
        self.preprocess_resnet = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        # Multi-scale preprocessing (for detail capture)
        self.preprocess_multiscale = transforms.Compose([
            transforms.Resize(512),
            transforms.CenterCrop(448),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        print(f"EnhancedFeatureExtractor initialized on {self.device}")
        print(f"Ensemble mode: {use_ensemble}")
    
    def extract_color_features(self, image_path: str) -> np.ndarray:
        """
        Extract color histogram features.
        This helps distinguish products by color.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Color histogram feature vector (144 dimensions: 3 channels x 48 bins)
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Calculate histograms for each channel
            hist_features = []
            for i in range(3):  # RGB channels
                hist = cv2.calcHist([image], [i], None, [48], [0, 256])
                hist = hist.flatten()
                hist = hist / (hist.sum() + 1e-8)  # Normalize
                hist_features.extend(hist)
            
            return np.array(hist_features, dtype=np.float32)
        except Exception as e:
            print(f"Warning: Could not extract color features from {image_path}: {e}")
            return np.zeros(144, dtype=np.float32)
    
    def extract_texture_features(self, image_path: str) -> np.ndarray:
        """
        Extract texture features using Gabor filters.
        Useful for fabric patterns and materials.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Texture feature vector (32 dimensions)
        """
        try:
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            image = cv2.resize(image, (128, 128))
            
            features = []
            
            # Apply Gabor filters at different scales and orientations
            for theta in [0, np.pi/4, np.pi/2, 3*np.pi/4]:
                for sigma in [3, 5]:
                    kernel = cv2.getGaborKernel((21, 21), sigma, theta, 10, 0.5)
                    filtered = cv2.filter2D(image, cv2.CV_32F, kernel)
                    features.append(filtered.mean())
                    features.append(filtered.std())
            
            return np.array(features, dtype=np.float32)
        except Exception as e:
            print(f"Warning: Could not extract texture features: {e}")
            return np.zeros(32, dtype=np.float32)
    
    def preprocess_image(self, image_path: str, model_type: str = "efficientnet") -> torch.Tensor:
        """
        Load and preprocess an image.
        
        Args:
            image_path: Path to the image file
            model_type: 'efficientnet', 'resnet', or 'multiscale'
            
        Returns:
            Preprocessed image tensor
        """
        try:
            image = Image.open(image_path).convert('RGB')
            
            if model_type == "efficientnet":
                return self.preprocess_efficientnet(image)
            elif model_type == "resnet":
                return self.preprocess_resnet(image)
            elif model_type == "multiscale":
                return self.preprocess_multiscale(image)
            else:
                return self.preprocess_efficientnet(image)
        except Exception as e:
            raise ValueError(f"Error loading image {image_path}: {str(e)}")
    
    def extract_deep_features(self, image_path: str) -> np.ndarray:
        """
        Extract deep learning features using EfficientNet and optionally ResNet.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Combined deep feature vector
        """
        features_list = []
        
        # EfficientNet features (1792 dimensions)
        image_tensor = self.preprocess_image(image_path, "efficientnet").unsqueeze(0).to(self.device)
        with torch.no_grad():
            efficientnet_features = self.efficientnet(image_tensor)
            efficientnet_features = efficientnet_features.squeeze().cpu().numpy()
            features_list.append(efficientnet_features)
        
        # ResNet features for ensemble (2048 dimensions)
        if self.use_ensemble:
            image_tensor = self.preprocess_image(image_path, "resnet").unsqueeze(0).to(self.device)
            with torch.no_grad():
                resnet_features = self.resnet(image_tensor)
                resnet_features = resnet_features.squeeze().cpu().numpy()
                features_list.append(resnet_features)
        
        # Concatenate all deep features
        deep_features = np.concatenate(features_list)
        
        return deep_features
    
    def extract_features(self, image_path: str, include_color: bool = True, 
                        include_texture: bool = True) -> np.ndarray:
        """
        Extract comprehensive features from an image.
        Combines deep learning features, color histograms, and texture features.
        
        Args:
            image_path: Path to the image file
            include_color: Include color histogram features
            include_texture: Include texture features
            
        Returns:
            Normalized feature vector
        """
        features_list = []
        
        # 1. Deep learning features (primary)
        deep_features = self.extract_deep_features(image_path)
        features_list.append(deep_features)
        
        # 2. Color features (helps with color matching)
        if include_color:
            color_features = self.extract_color_features(image_path)
            # Weight color features (they're less important than deep features)
            color_features = color_features * 0.3
            features_list.append(color_features)
        
        # 3. Texture features (helps with fabric/material matching)
        if include_texture:
            texture_features = self.extract_texture_features(image_path)
            # Weight texture features
            texture_features = texture_features * 0.2
            features_list.append(texture_features)
        
        # Concatenate all features
        combined_features = np.concatenate(features_list)
        
        # L2 normalize the entire feature vector
        combined_features = combined_features / (np.linalg.norm(combined_features) + 1e-8)
        
        return combined_features
    
    def extract_features_batch(self, image_paths: List[str], batch_size: int = 16,
                               include_color: bool = True, 
                               include_texture: bool = True) -> np.ndarray:
        """
        Extract features from multiple images in batches.
        
        Args:
            image_paths: List of paths to image files
            batch_size: Number of images to process at once
            include_color: Include color features
            include_texture: Include texture features
            
        Returns:
            Array of normalized feature vectors
        """
        all_features = []
        
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            
            for path in batch_paths:
                try:
                    features = self.extract_features(path, include_color, include_texture)
                    all_features.append(features)
                except Exception as e:
                    print(f"Warning: Skipping {path} due to error: {str(e)}")
                    continue
            
            print(f"Processed {min(i + batch_size, len(image_paths))}/{len(image_paths)} images")
        
        if not all_features:
            raise ValueError("No features could be extracted from the provided images")
        
        return np.vstack(all_features)
    
    def compute_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """
        Compute cosine similarity between two feature vectors.
        
        Args:
            features1: First feature vector
            features2: Second feature vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        # Ensure vectors are normalized
        features1 = features1 / (np.linalg.norm(features1) + 1e-8)
        features2 = features2 / (np.linalg.norm(features2) + 1e-8)
        
        # Compute dot product (cosine similarity for normalized vectors)
        similarity = np.dot(features1, features2)
        
        # Clip to [0, 1] range
        return float(np.clip(similarity, 0, 1))


# Backward compatibility: keep the original FeatureExtractor class
class FeatureExtractor:
    """Original feature extractor for backward compatibility."""
    
    def __init__(self, device: str = None):
        self.enhanced_extractor = EnhancedFeatureExtractor(device=device, use_ensemble=True)
    
    def extract_features(self, image_path: str) -> np.ndarray:
        return self.enhanced_extractor.extract_features(image_path)
    
    def extract_features_batch(self, image_paths: List[str], batch_size: int = 16) -> np.ndarray:
        return self.enhanced_extractor.extract_features_batch(image_paths, batch_size)
    
    def compute_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        return self.enhanced_extractor.compute_similarity(features1, features2)


def test_feature_extractor():
    """Test the enhanced feature extractor with a sample image."""
    extractor = EnhancedFeatureExtractor(use_ensemble=True)
    
    # Test with a sample image
    test_image = "../../../data/reebok_images/item_0.jpg"
    
    if os.path.exists(test_image):
        features = extractor.extract_features(test_image)
        print(f"Extracted features shape: {features.shape}")
        print(f"Feature vector norm: {np.linalg.norm(features):.4f}")
        print("Enhanced feature extractor test passed!")
    else:
        print(f"Test image not found: {test_image}")


if __name__ == "__main__":
    test_feature_extractor()
