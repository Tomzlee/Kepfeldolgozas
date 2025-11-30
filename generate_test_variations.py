"""
Generate noisy and rotated test image variations for testing the evaluation system.
"""
import cv2
import numpy as np
import os
import sys

def add_noise_to_image(image_path, output_path, noise_level='medium'):
    """
    Add various types of noise to simulate a dirty/scanned document.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")

    # Set noise parameters based on level
    if noise_level == 'light':
        salt_pepper_amount = 0.001
        gaussian_std = 3
        num_dirt_spots = 10
    elif noise_level == 'medium':
        salt_pepper_amount = 0.003
        gaussian_std = 5
        num_dirt_spots = 25
    else:  # heavy
        salt_pepper_amount = 0.008
        gaussian_std = 8
        num_dirt_spots = 50

    noisy_img = img.copy()

    # 1. Add salt and pepper noise (random black/white pixels)
    h, w = noisy_img.shape[:2]
    num_salt = int(salt_pepper_amount * h * w)

    # Salt (white pixels)
    coords = [np.random.randint(0, i, num_salt) for i in (h, w)]
    noisy_img[coords[0], coords[1]] = 255

    # Pepper (black pixels)
    coords = [np.random.randint(0, i, num_salt) for i in (h, w)]
    noisy_img[coords[0], coords[1]] = 0

    # 2. Add Gaussian noise
    gaussian_noise = np.random.normal(0, gaussian_std, noisy_img.shape)
    noisy_img = np.clip(noisy_img + gaussian_noise, 0, 255).astype(np.uint8)

    # 3. Add random "dirt spots" (small blobs)
    for _ in range(num_dirt_spots):
        x = np.random.randint(0, w - 50)
        y = np.random.randint(0, h - 50)
        spot_size = np.random.randint(5, 30)
        intensity = np.random.randint(50, 150)

        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (x + spot_size // 2, y + spot_size // 2),
                   spot_size // 2, 255, -1)

        alpha = 0.4
        noisy_img = np.where(mask[:, :, np.newaxis] == 255,
                             noisy_img * (1 - alpha) + intensity * alpha,
                             noisy_img).astype(np.uint8)

    # 4. Simulate slight blur from scanning
    noisy_img = cv2.GaussianBlur(noisy_img, (3, 3), 0.5)

    cv2.imwrite(output_path, noisy_img)
    print(f"[OK] Noisy image ({noise_level}) saved: {output_path}")
    return noisy_img


def rotate_image(image_path, output_path, angle=None, add_perspective=True):
    """
    Rotate image to simulate misaligned scanning.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")

    h, w = img.shape[:2]

    # Use provided angle or generate random one
    if angle is None:
        angle = np.random.uniform(-8, 8)

    # Get rotation matrix
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Calculate new image size to fit rotated image
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))

    # Adjust rotation matrix for new size
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]

    # Apply rotation
    rotated_img = cv2.warpAffine(img, rotation_matrix, (new_w, new_h),
                                  borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=(255, 255, 255))

    # Optionally add perspective distortion
    if add_perspective:
        h_rot, w_rot = rotated_img.shape[:2]

        # Define source points (corners of the image)
        pts1 = np.float32([
            [0, 0],
            [w_rot, 0],
            [0, h_rot],
            [w_rot, h_rot]
        ])

        # Define destination points with slight perspective shift
        shift = 20  # pixels
        pts2 = np.float32([
            [np.random.randint(-shift, shift), np.random.randint(-shift, shift)],
            [w_rot + np.random.randint(-shift, shift), np.random.randint(-shift, shift)],
            [np.random.randint(-shift, shift), h_rot + np.random.randint(-shift, shift)],
            [w_rot + np.random.randint(-shift, shift), h_rot + np.random.randint(-shift, shift)]
        ])

        # Apply perspective transform
        perspective_matrix = cv2.getPerspectiveTransform(pts1, pts2)
        rotated_img = cv2.warpPerspective(rotated_img, perspective_matrix, (w_rot, h_rot),
                                          borderMode=cv2.BORDER_CONSTANT,
                                          borderValue=(255, 255, 255))

    cv2.imwrite(output_path, rotated_img)
    print(f"[OK] Rotated image (angle: {angle:.2f} degrees) saved: {output_path}")
    return rotated_img


def main():
    """Generate test image variations."""

    # Original test image
    original_image = "tesztkep.png"

    # Check if original exists
    if not os.path.exists(original_image):
        print(f"[WARNING] Original image not found: {original_image}")
        print("   Please run tesztlapgeneralas.py first to generate the base image.")
        sys.exit(1)

    print(f"[INFO] Using original image: {original_image}")
    print()

    # Generate noisy version
    print("[INFO] Generating noisy test image...")
    noisy_output = "tesztkep_noisy.png"
    add_noise_to_image(original_image, noisy_output, noise_level='medium')
    print()

    # Generate rotated version
    print("[INFO] Generating rotated test image...")
    rotated_output = "tesztkep_rotated.png"
    rotate_image(original_image, rotated_output, angle=5.5, add_perspective=True)
    print()

    # Generate combination: noisy + slightly rotated
    print("[INFO] Generating noisy + rotated test image...")
    temp_rotated = "temp_rotated.png"
    rotate_image(original_image, temp_rotated, angle=3.2, add_perspective=True)
    combo_output = "tesztkep_noisy_rotated.png"
    add_noise_to_image(temp_rotated, combo_output, noise_level='light')
    if os.path.exists(temp_rotated):
        os.remove(temp_rotated)
    print()

    print("=" * 60)
    print("[OK] All test variations generated successfully!")
    print("=" * 60)
    print("\nGenerated files:")
    print(f"  1. {noisy_output} - Image with dirt and scanner noise")
    print(f"  2. {rotated_output} - Rotated image with perspective distortion")
    print(f"  3. {combo_output} - Both noisy and rotated")
    print("\nYou can now test the evaluation system with these challenging images!")


if __name__ == "__main__":
    main()
