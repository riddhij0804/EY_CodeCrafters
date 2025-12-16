# Feature Extractor using Enhanced Models
# Extracts visual features from images for similarity search
# Supports both simple (ResNet50) and enhanced (EfficientNet + ensemble) modes

import os
# Fix for OpenMP library conflict
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from typing import Union, List
import cv2


class FeatureExtractor:
    """
    Feature extractor with support for multiple models and accuracy modes.
    
    Modes:
    - 'simple': ResNet50 only (fast, good accuracy)
    - 'enhanced': EfficientNet-B4 + color + texture (slower, better accuracy)
    - 'ensemble': EfficientNet + ResNet + color + texture (slowest, best accuracy)
    """
    
    def __init__(self, device: str = None, mode: str = 'enhanced'):
        """
        Initialize the feature extractor.
        
        Args:
            device: 'cuda' or 'cpu'. If None, automatically selects based on availability.
            mode: 'simple', 'enhanced', or 'ensemble' for accuracy vs speed tradeoff
        """
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        self.mode = mode
        print(f"Initializing FeatureExtractor in '{mode}' mode...")
        
        # Load primary model based on mode
        if mode in ['enhanced', 'ensemble']:
            # Use EfficientNet-B4 for better accuracy
            print("Loading EfficientNet-B4...")
            self.model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.IMAGENET1K_V1)
            self.model.classifier = nn.Identity()
            self.model_input_size = 380
        else:
            # Use ResNet50 for speed
            print("Loading ResNet50...")
            self.model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
            self.model = nn.Sequential(*list(self.model.children())[:-1])
            self.model_input_size = 224
        
        
        # Set to evaluation mode
        self.model.eval()
        self.model.to(self.device)
        
        # Load secondary model for ensemble mode
        self.model2 = None
        if mode == 'ensemble':
            print("Loading ResNet50 for ensemble...")
            self.model2 = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
            self.model2 = nn.Sequential(*list(self.model2.children())[:-1])
            self.model2.eval()
            self.model2.to(self.device)
        
        # Define image preprocessing pipeline
        resize_size = int(self.model_input_size * 1.14)  # Standard practice
        self.preprocess = transforms.Compose([
            transforms.Resize(resize_size),
            transforms.CenterCrop(self.model_input_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        # Preprocessing for secondary model (if ensemble)
        if self.model2:
            self.preprocess2 = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
        
        print(f"FeatureExtractor initialized on {self.device} (mode: {mode})")
    
    def preprocess_image(self, image_path: str) -> torch.Tensor:
        """
        Load and preprocess an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image tensor
        """
        try:
            image = Image.open(image_path).convert('RGB')
            return self.preprocess(image)
        except Exception as e:
            raise ValueError(f"Error loading image {image_path}: {str(e)}")
    
    def extract_color_features(self, image_path: str) -> np.ndarray:
        """
        Extract color histogram features (helps with color matching).
        """
        try:
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            hist_features = []
            for i in range(3):  # RGB channels
                hist = cv2.calcHist([image], [i], None, [32], [0, 256])
                hist = hist.flatten()
                hist = hist / (hist.sum() + 1e-8)
                hist_features.extend(hist)
            
            return np.array(hist_features, dtype=np.float32)
        except:
            return np.zeros(96, dtype=np.float32)
    
    def extract_features(self, image_path: str) -> np.ndarray:
        """
        Extract comprehensive features from a single image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Normalized feature vector
        """
        features_list = []
        
        # 1. Primary deep learning features
        image_tensor = self.preprocess_image(image_path).unsqueeze(0).to(self.device)
        with torch.no_grad():
            features = self.model(image_tensor)
        features = features.squeeze().cpu().numpy()
        features_list.append(features)
        
        # 2. Secondary model features (ensemble mode)
        if self.mode == 'ensemble' and self.model2 is not None:
            image = Image.open(image_path).convert('RGB')
            image_tensor2 = self.preprocess2(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                features2 = self.model2(image_tensor2)
            features2 = features2.squeeze().cpu().numpy()
            features_list.append(features2 * 0.7)  # Weight secondary model
        
        # 3. Color features (enhanced/ensemble modes)
        if self.mode in ['enhanced', 'ensemble']:
            color_features = self.extract_color_features(image_path)
            features_list.append(color_features * 0.3)  # Weight color features
        
        # Concatenate all features
        combined_features = np.concatenate(features_list)
        
        # L2 normalize
        combined_features = combined_features / (np.linalg.norm(combined_features) + 1e-8)
        
        return combined_features
    
    def extract_features_batch(self, image_paths: List[str], batch_size: int = 16) -> np.ndarray:
        """
        Extract features from multiple images in batches.
        
        Args:
            image_paths: List of paths to image files
            batch_size: Number of images to process at once (reduced for enhanced mode)
            
        Returns:
            Array of normalized feature vectors
        """
        all_features = []
        
        # In enhanced/ensemble mode, process individually due to color features
        if self.mode in ['enhanced', 'ensemble']:
            for i, path in enumerate(image_paths):
                try:
                    features = self.extract_features(path)
                    all_features.append(features)
                    if (i + 1) % 10 == 0:
                        print(f"Processed {i + 1}/{len(image_paths)} images")
                except Exception as e:
                    print(f"Warning: Skipping {path} due to error: {str(e)}")
                    continue
        else:
            # Simple mode: batch processing
            for i in range(0, len(image_paths), batch_size):
                batch_paths = image_paths[i:i + batch_size]
                batch_tensors = []
                
                for path in batch_paths:
                    try:
                        tensor = self.preprocess_image(path)
                        batch_tensors.append(tensor)
                    except Exception as e:
                        print(f"Warning: Skipping {path} due to error: {str(e)}")
                        continue
                
                if not batch_tensors:
                    continue
                
                # Stack tensors and move to device
                batch = torch.stack(batch_tensors).to(self.device)
                
                # Extract features
                with torch.no_grad():
                    features = self.model(batch)
                
                # Flatten and convert to numpy
                features = features.squeeze().cpu().numpy()
                
                # Handle single image case
                if len(batch_tensors) == 1:
                    features = features.reshape(1, -1)
                
                # Normalize each feature vector
                norms = np.linalg.norm(features, axis=1, keepdims=True) + 1e-8
                features = features / norms
                
                all_features.append(features)
                
                print(f"Processed {i + len(batch_tensors)}/{len(image_paths)} images")
        
        if not all_features:
            raise ValueError("No features could be extracted from the provided images")
        
        if self.mode in ['enhanced', 'ensemble']:
            return np.vstack(all_features)
        else:
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


def test_feature_extractor():
    """Test the feature extractor with a sample image."""
    extractor = FeatureExtractor()
    
    # Test with a sample image (replace with actual path)
    test_image = "../../data/reebok_images/item_0.jpg"
    
    if os.path.exists(test_image):
        features = extractor.extract_features(test_image)
        print(f"Extracted features shape: {features.shape}")
        print(f"Feature vector norm: {np.linalg.norm(features):.4f}")
        print("Feature extractor test passed!")
    else:
        print(f"Test image not found: {test_image}")


if __name__ == "__main__":
    test_feature_extractor()
