"""Dataset utilities for aquaculture disease classification."""
from pathlib import Path
from PIL import Image
import os

# Define known disease labels
LABEL_MAP = {
    'healthy': 0,
    'red_paste': 1,
    'fungus': 2,
    'bacterial': 3,
    'parasitic': 4,
    'unknown': 5
}

# Expected directory structure:
# data/samples/
#   - healthy.jpg
#   - red_paste.jpg
#   - fungus.jpg
#   - bacterial.jpg
#   - parasitic.jpg
#   - unknown.jpg

def get_sample_images(sample_dir: str = "data/samples") -> list:
    """Get list of image files from sample directory."""
    if not os.path.exists(sample_dir):
        print(f"Sample directory not found: {sample_dir}")
        return []

    images = []
    for f in os.listdir(sample_dir):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            images.append(os.path.join(sample_dir, f))
    return images

def load_image(path: str) -> Image.Image:
    """Load and resize image to 224x224."""
    img = Image.open(path).convert('RGB')
    img = img.resize((224, 224))
    return img

def create_dummy_samples():
    """Create dummy sample images for testing."""
    import tempfile
    import shutil

    # Create temp directory
    tmp_dir = tempfile.mkdtemp(prefix="aqua_demo_")

    # Create dummy images (using solid colors)
    for i in range(10):
        img = Image.new('RGB', (224, 224), color=(i*30, 50, 100))
        img.save(os.path.join(tmp_dir, f"sample_{i}.jpg"))

    return tmp_dir

if __name__ == "__main__":
    print("Sample image loader ready")
    print(f"Expected samples in: {Path('data/samples').absolute()}")
