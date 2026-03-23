"""
Face Manager - Handles face recognition and management of authorized faces
"""

import face_recognition
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import pickle
import json
from datetime import datetime
import threading
import shutil

class FaceManager:
    """Manages face recognition and authorized face database"""
    
    def __init__(self, authorized_dir: str = "data\\images\\authorized"):
        self.authorized_dir = Path(authorized_dir)
        self.authorized_dir.mkdir(parents=True, exist_ok=True)
        
        self.known_face_encodings = []
        self.known_face_names = []
        self.face_metadata = {}
        
        self._lock = threading.Lock()
        self._encodings_cache_file = self.authorized_dir / ".face_encodings.pkl"
        self._metadata_file = self.authorized_dir / ".face_metadata.json"
        
        self.load_authorized_faces()
    
    def load_authorized_faces(self):
        """Load authorized face encodings from directory"""
        with self._lock:
            # Try to load from cache first
            if self._load_from_cache():
                print(f"Loaded {len(self.known_face_names)} faces from cache")
                return
            
            # Otherwise, load from images
            self.known_face_encodings = []
            self.known_face_names = []
            self.face_metadata = {}
            
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
            face_files = [f for f in self.authorized_dir.iterdir() 
                         if f.suffix.lower() in image_extensions]
            
            for image_path in face_files:
                try:
                    # Load image
                    image = face_recognition.load_image_file(str(image_path))
                    
                    # Find face encodings
                    encodings = face_recognition.face_encodings(image)
                    
                    if encodings:
                        # Use first face found
                        self.known_face_encodings.append(encodings[0])
                        self.known_face_names.append(image_path.stem)
                        
                        # Store metadata
                        self.face_metadata[image_path.stem] = {
                            'file': image_path.name,
                            'added': datetime.now().isoformat(),
                            'encoding_count': len(encodings)
                        }
                        
                        print(f"Loaded face: {image_path.stem}")
                    else:
                        print(f"No face found in: {image_path.name}")
                        
                except Exception as e:
                    print(f"Error loading {image_path.name}: {e}")
            
            # Save to cache
            self._save_to_cache()
            self._save_metadata()
            
            print(f"Total authorized faces loaded: {len(self.known_face_names)}")
    
    def recognize_faces(self, frame: np.ndarray, 
                       return_encodings: bool = False) -> List[Tuple[str, Tuple[int, int, int, int]]]:
        """
        Recognize faces in frame and return names with locations
        Returns: List of (name, (top, right, bottom, left))
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Resize frame for faster processing
        scale = 0.25
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=scale, fy=scale)
        
        # Find all face locations and encodings
        face_locations = face_recognition.face_locations(small_frame, model="hog")
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        
        face_data = []
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Scale back up face locations
            top = int(top / scale)
            right = int(right / scale)
            bottom = int(bottom / scale)
            left = int(left / scale)
            
            # Check if face matches known faces
            name = "Unknown"
            
            if self.known_face_encodings:
                # Compare faces
                matches = face_recognition.compare_faces(
                    self.known_face_encodings, 
                    face_encoding,
                    tolerance=0.6
                )
                
                # Find best match
                face_distances = face_recognition.face_distance(
                    self.known_face_encodings, 
                    face_encoding
                )
                
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
            
            face_data.append((name, (top, right, bottom, left)))
            
        return face_data
    
    def add_authorized_face(self, name: str, image_path: str) -> bool:
        """Add new authorized face from image file"""
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Find face encodings
            encodings = face_recognition.face_encodings(image)
            
            if not encodings:
                print(f"No face found in image: {image_path}")
                return False
            
            if len(encodings) > 1:
                print(f"Warning: Multiple faces found. Using the first one.")
            
            with self._lock:
                # Add to known faces
                self.known_face_encodings.append(encodings[0])
                self.known_face_names.append(name)
                
                # Copy image to authorized directory
                image_filename = f"{name}.jpg"
                dest_path = self.authorized_dir / image_filename
                
                # Convert and save as JPEG
                bgr_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(dest_path), bgr_image)
                
                # Update metadata
                self.face_metadata[name] = {
                    'file': image_filename,
                    'added': datetime.now().isoformat(),
                    'encoding_count': len(encodings),
                    'original_path': str(image_path)
                }
                
                # Save cache and metadata
                self._save_to_cache()
                self._save_metadata()
                
            print(f"Successfully added {name} to authorized faces")
            return True
            
        except Exception as e:
            print(f"Error adding face: {e}")
            return False
    
    def remove_authorized_face(self, name: str) -> bool:
        """Remove authorized face"""
        with self._lock:
            if name not in self.known_face_names:
                return False
            
            # Find index
            index = self.known_face_names.index(name)
            
            # Remove from lists
            del self.known_face_names[index]
            del self.known_face_encodings[index]
            
            # Remove metadata
            if name in self.face_metadata:
                # Delete image file
                image_file = self.authorized_dir / self.face_metadata[name]['file']
                if image_file.exists():
                    image_file.unlink()
                
                del self.face_metadata[name]
            
            # Update cache
            self._save_to_cache()
            self._save_metadata()
            
            return True
    
    def list_authorized_faces(self) -> List[str]:
        """Get list of all authorized face names"""
        return self.known_face_names.copy()
    
    def get_face_info(self, name: str) -> Optional[Dict]:
        """Get metadata for a specific face"""
        return self.face_metadata.get(name)
    
    def update_face_encoding(self, name: str, new_image_path: str) -> bool:
        """Update encoding for existing face"""
        if name not in self.known_face_names:
            return False
        
        # Remove old face
        self.remove_authorized_face(name)
        
        # Add new face
        return self.add_authorized_face(name, new_image_path)
    
    def _save_to_cache(self):
        """Save face encodings to cache file"""
        try:
            cache_data = {
                'encodings': self.known_face_encodings,
                'names': self.known_face_names,
                'version': 1
            }
            
            with open(self._encodings_cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
                
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def _load_from_cache(self) -> bool:
        """Load face encodings from cache file"""
        try:
            if not self._encodings_cache_file.exists():
                return False
            
            with open(self._encodings_cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            self.known_face_encodings = cache_data.get('encodings', [])
            self.known_face_names = cache_data.get('names', [])
            
            # Load metadata
            if self._metadata_file.exists():
                with open(self._metadata_file, 'r') as f:
                    self.face_metadata = json.load(f)
            
            return True
            
        except Exception as e:
            print(f"Error loading cache: {e}")
            return False
    
    def _save_metadata(self):
        """Save face metadata to file"""
        try:
            with open(self._metadata_file, 'w') as f:
                json.dump(self.face_metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def verify_face(self, face_encoding: np.ndarray, name: str) -> Tuple[bool, float]:
        """Verify if a face encoding matches a specific person"""
        if name not in self.known_face_names:
            return False, 1.0
        
        index = self.known_face_names.index(name)
        distance = face_recognition.face_distance(
            [self.known_face_encodings[index]], 
            face_encoding
        )[0]
        
        # Threshold for verification
        is_match = distance < 0.6
        
        return is_match, float(distance)
    
    def find_similar_faces(self, face_encoding: np.ndarray, 
                          threshold: float = 0.6) -> List[Tuple[str, float]]:
        """Find all similar faces to the given encoding"""
        if not self.known_face_encodings:
            return []
        
        distances = face_recognition.face_distance(
            self.known_face_encodings, 
            face_encoding
        )
        
        similar_faces = []
        for i, distance in enumerate(distances):
            if distance < threshold:
                similar_faces.append((self.known_face_names[i], float(distance)))
        
        # Sort by distance (most similar first)
        similar_faces.sort(key=lambda x: x[1])
        
        return similar_faces