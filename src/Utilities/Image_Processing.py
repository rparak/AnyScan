## =========================================================================== ## 
# MIT License
# Copyright (c) 2024 Roman Parak
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
## =========================================================================== ## 
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: Image_Processing.py
## =========================================================================== ##

# Numpy (Array computing)
import numpy as np
# Typing (Support for type hints)
import typing as tp
# OpenCV (Computer Vision)
import cv2
# Custom Lib.:
#   ../Utilities/General
import Utilities.General
#   ../Transformation/Utilities/Mathematics
import Transformation.Utilities.Mathematics as Mathematics

def Get_Alpha_Beta_Parameters(image: tp.List[tp.List[int]], clip_limit: float) -> tp.Tuple[float, float]:
    """
    Description:
        Function to adjust the contrast and brightness parameters of the input image by clipping the histogram.

        The main core of the function is to obtain the alpha and beta parameters 
        to determine the equation:
            g(i, j) = alpha * f(i, j) + beta,

            where g(i, j) are the input (source) pixels of the image, f(i, j) are the output pixels 
            of the image, and alpha, beta are the contrast and brightness parameters.

    Args:
        (1) image [Vector<float> Image Shape {Resolution<x, y>}]: Input raw image.
        (2) clip_limit [float]: Parameter for histogram clipping in percentage.

    Returns:
        (1) parameter [float]: A gain (contrast) parameter called alpha.
        (2) parameter [float]: A bias (brightness) parameter called beta.
    """

    image_copy = image.copy()

    # Calculate the grayscale histogram of the image.
    image_hist = cv2.calcHist([image_copy], [0], None, [256], [0, 256])

    # Get the cumulative sum of the elements (histogram).
    c_hist = np.cumsum(image_hist)

    # Modify the percentage to clip the histogram.
    c_hist_max = c_hist[-1]
    clip_limit_mod = clip_limit * (c_hist_max/float(100.0*2.0))

    # Clip the histogram if the values are outside the limit.
    min_value = 0; max_value = c_hist.size - 1
    for _, c_hist_i in enumerate(c_hist):
        if c_hist_i < clip_limit_mod:
            min_value += 1

        if c_hist_i >= (c_hist_max - clip_limit_mod):
            max_value -= 1

    # Express the alpha and beta parameters.
    #   Gain (contrast) parameter.
    alpha = 255 / (max_value - min_value)
    #   Bias (brightness) parameter.
    beta  = (-1) * (min_value * alpha)

    return (alpha, beta)

def Draw_Bounding_Box(image: tp.List[tp.List[int]], bounding_box_properties: tp.Tuple[str, str, tp.List[tp.Union[int, float]]], format: str, Color: tp.List[int], 
                      fill_box: bool, show_info: bool) -> tp.List[tp.List[int]]:
    """
    Description:
        Function to draw the bounding box of an object with additional dependencies (name, precision, etc.) in the raw image.

    Args:
        (1) image [Vector<float> Image Shape {Resolution<x, y>}]: Input raw image.
        (2) bounding_box_properties [Dictionary {'Name': string, 'Precision', string, 
                                                 'Data': Vector<int/float> 1x4}]: Bounding box properties.
        (3) format [string]: The format of the bounding box input data. Available formats: YOLO, Pascal_VOC.
        (4) Color [Vector<float> 1x3]: Color of the box and other dependencies.
        (5) fill_box [bool]: Information about whether or not to fill the rectangle.
        (6) show_info [bool]: Information about whether or not to show additional text.

    Returns:
        (1) parameter [Vector<float> Image Shape {Resolution<x, y>}]: Output image extended with bounding box and other dependencies.

    Example:
        image_out = Draw_Bounding_Box(image, bounding_box_properties = {'Name': 'Obj_Name_Id_0', 'Precision': '100', 'Data': None}, format = 'YOLO/Pascal_VOC', 
                                      Color = (0, 255, 0), fill_box = False, show_info = False)
    """

    image_out = image.copy()

    # Set the properties of the drawing bounding box.
    #   Image Resolution: [x: Height, y: Width]
    Resolution = {'x': image_out.shape[1], 'y': image_out.shape[0]}
    #   Line width of the rectangle.
    line_width = 2

    # Obtain data in PASCAL_VOC format to determine the bounding box to be rendered.
    #   data = {'x_min', 'y_min', 'x_max', 'y_max'}
    if format == 'YOLO':
        data = Utilities.General.Convert_Boundig_Box_Data(format, 'PASCAL_VOC', bounding_box_properties['Data'], Resolution)
    elif format == 'PASCAL_VOC':
        data = bounding_box_properties['Data']

    x_min = data['x_min']; y_min = data['y_min']
    x_max = data['x_max']; y_max = data['y_max']
    box_w = x_max - x_min; box_h = y_max - y_min

    # Fill the box with the desired transparency coefficient.
    if fill_box == True:
        # Transparency coefficient.
        alpha = 0.10

        # The main rectangle that bounds the object.
        cv2.rectangle(image_out, (x_min, y_min), (x_max, y_max), Color, -1)
            
        # Change from one image to another. To blend the image, add weights that determine 
        # the transparency and translucency of the images.
        image_out = cv2.addWeighted(image_out, alpha, image, 1 - alpha, 0)

    test_var = 8.0

    #  --          --
    # |              |    
    #      Object    
    # |              |
    #  --          --
    #   Corner: Left Top
    cv2.line(image_out, (x_min, y_min), (x_min + int(box_w/test_var), y_min), Color, line_width)
    cv2.line(image_out, (x_min, y_min), (x_min, y_min + int(box_h/test_var)), Color, line_width)
    #   Corner: Left Bottom
    cv2.line(image_out, (x_min, y_max), (x_min + int(box_w/test_var), y_max), Color, line_width)
    cv2.line(image_out, (x_min, y_max), (x_min, y_max - int(box_h/test_var)), Color, line_width)
    #   Corner: Right Top
    cv2.line(image_out, (x_max, y_min), (x_max - int(box_w/test_var), y_min), Color, line_width)
    cv2.line(image_out, (x_max, y_min), (x_max, y_min + int(box_h/test_var)), Color, line_width)
    #   Corner: Right Bottom
    cv2.line(image_out, (x_max, y_max), (x_max - int(box_w/test_var), y_max), Color, line_width)
    cv2.line(image_out, (x_max, y_max), (x_max, y_max - int(box_h/test_var)), Color, line_width)

    # Show additional information such as name and precision.
    if show_info == True:
        cv2.putText(image_out, f"Class {bounding_box_properties['Name']}: {bounding_box_properties['Precision']}", 
                    (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, Color, 2)

    return image_out

def YOLO_ONNX_Format_Object_Detection(image: tp.List[tp.List[int]], model_onnx: str, image_size: int, confidence: float,
                                      iou: float) -> tp.Tuple[tp.List[int], tp.List[float], tp.Tuple[str, str, tp.List[tp.Union[int, float]]]]:
    """
    Description:
        Function for object detection using the trained YOLO model. The model in our case must be in *.onnx format, converted 
        from the official *.pt model.

        More information about training, validation, etc. of the model can be found here:
            ../src/Training/..

    Args:
        (1) image [Vector<float> Image Shape {Resolution<x, y>}]: Input image to be used for object detection.
        (2) model_onnx [str]: Input model in *.onnx format.
                              Note:
                                More information about the onnx format can be found at: https://onnx.ai
        (3) image_size [Vector<float> 1x2]: The size of the input image. The size must match the size of the image when training the model.
        (4) confidence [float]: The threshold used to filter the bounding boxes by score.
        (5) iou [float]: Threshold used for non-maximum suppression.
    
    Returns:
        (1) parameter [int or Vector<int> 1xn]: The class ID of the detected object.
        (2) parameter [float or Vector<float> 1xn]: The actual object confidence threshold for detection.
        (3) parameter [Dictionary {'x_min': int, 'y_min': int, 
                                   'x_max': int, 'y_max': int} x n]: Bounding box in the PASCAL VOC format 
                                                                     on the actual image size.
        Note:
            Where n is the number of detected objects.
    """

    # Parameters:
    #   Image Resolution: [x: Height, y: Width]
    Resolution = {'x': image.shape[1], 'y': image.shape[0]}
    #   The coefficient (factor) of the processed image.
    Image_Coeff = {'x': Resolution['x'] / image_size[0], 
                   'y': Resolution['y'] / image_size[1]}

    # Create a blob from the input image.
    blob = cv2.dnn.blobFromImage(image, 1.0/255.0, (image_size[0], image_size[1]), swapRB=True, crop=False)

    # Get the names of the output layers.
    layer_names = model_onnx.getLayerNames()
    layer_names = [layer_names[i - 1] for i in model_onnx.getUnconnectedOutLayers()]

    # Perform a forward pass through the YOLO object detector to obtain bounding 
    # boxes and associated probabilities.
    model_onnx.setInput(blob)
    output_layers = model_onnx.forward(layer_names)

    # Find the bounding boxes that correspond to the input object detection parameters.
    class_ids = []; bounding_boxes = []; confidences = []
    for _, output_layers_i in enumerate(output_layers):
        for _, output_layers_ij in enumerate(output_layers_i.T):
            # Extract the class identification number (class id) and the confidence 
            # of the actual object detection.
            scores_tmp = output_layers_ij[4:]; class_id_tmp = Mathematics.Max(scores_tmp)[0]
            confidence_tmp = scores_tmp[class_id_tmp]

            # Consider only predictions that are higher than the desired confidence value specified 
            # by the function input.
            if confidence_tmp > confidence:
                # Add the class id and confidence to the list. 
                class_ids.append(class_id_tmp); confidences.append(confidence_tmp[0])
                # Extract the coordinates (YOLO) of the bounding box.
                bounding_box_tmp = output_layers_ij[0:4].reshape(1, 4)[0]
                #   Convert the coordinates of the bounding box to the desired format.
                x = int((bounding_box_tmp[0] - 0.5 * bounding_box_tmp[2]) * Image_Coeff['x'])
                y = int((bounding_box_tmp[1] - 0.5 * bounding_box_tmp[3]) * Image_Coeff['y'])
                w = int(bounding_box_tmp[2] * Image_Coeff['x'])
                h = int(bounding_box_tmp[3] * Image_Coeff['y'])
                # Add a bounding box to the list.
                bounding_boxes.append([x, y, w, h])

    # Perform a non-maximal suppression relative to the previously defined score.
    indexes = cv2.dnn.NMSBoxes(bounding_boxes, confidences, confidence, iou)
 
    # At least one detection should be successful, otherwise just report a failed detection.
    if isinstance(indexes, np.ndarray):
        print(f'[INFO] The model found {indexes.size} object in the input image.')

        # Store parameters over specific indexes.
        class_ids_out = []; bounding_boxes_out = []; confidences_out = []
        for i in indexes.flatten():
            # Extract the class identification number (class id) and the confidence.
            class_ids_out.append(class_ids[i]); confidences_out.append(confidences[i])
            # Extract the bounding box and convert it to PASCAL VOC format.
            bounding_boxes_out.append({'x_min': bounding_boxes[i][0], 
                                       'y_min': bounding_boxes[i][1], 
                                       'x_max': bounding_boxes[i][0] + bounding_boxes[i][2], 
                                       'y_max': bounding_boxes[i][1] + bounding_boxes[i][3]})
            
        return (class_ids_out, bounding_boxes_out, confidences_out)

    else:
        print('[INFO] The model did not find object in the input image.')
        return (None, None, None)
    
class Process_Image_Cls:
    """
    Description:
        A class for processing images based on the type ('synthetic' or 'real').

    Note:
        Includes methods for adding Gaussian noise, adjusting color style, and applying Gaussian blur.
    
    Args:
        (1) image_type [str]: Type of the image to process. Must be either 'synthetic' or 'real'.
    """

    def __init__(self, image_type: str):
        if image_type not in ['synthetic', 'real']:
            raise ValueError("[ERROR] Image type must be 'synthetic' or 'real'.")
        self.__image_type = image_type

    def __Noise(self, image: np.ndarray, std_dev: float = 5.0) -> np.ndarray:
        """
        Description:
            Adds Gaussian noise to an image to simulate sensor noise in synthetic data.

        Args:
            (1) image [np.ndarray]: Input image in uint8 format.
            (2) std_dev [float]: Standard deviation of the Gaussian noise.

        Returns:
            (1) parameter [np.ndarray]: Output image with added noise.
        """

        random_noise = np.random.normal(0, std_dev, image.shape).astype(np.int16)
        noisy_img = image.astype(np.int16) + random_noise
        return np.clip(noisy_img, 0, 255).astype(np.uint8)

    def __Color_Style(self, image: np.ndarray, alpha: float = 0.95, beta: int = 5) -> np.ndarray:
        """
        Description:
            Adjusts brightness and contrast, with optional warm filter effect.

        Args:
            (1) image [np.ndarray]: Input image.
            (2) alpha [float]: Contrast factor (1.0 = no change).
            (3) beta [int]: Brightness offset.

        Returns:
            (1) parameter [np.ndarray]: Color-adjusted image.
        """

        adjusted_img = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        return np.clip(adjusted_img * np.array([[[1.0, 1.0, 1.0]]]), 0, 255).astype(np.uint8)

    def __Blur(self, image: np.ndarray, kernel_size: tp.Tuple[int, int] = (5, 5), sigma: float = 1.0) -> np.ndarray:
        """
        Description:
            Applies Gaussian blur to reduce sharpness and simulate camera effects.

        Args:
            (1) image [np.ndarray]: Input image.
            (2) kernel_size [Tuple[int, int]]: Size of the Gaussian kernel.
            (3) sigma [float]: Gaussian kernel standard deviation.

        Returns:
            (1) parameter [np.ndarray]: Blurred image.
        """

        return cv2.GaussianBlur(image, kernel_size, sigmaX=sigma)

    def Apply(self, image: np.ndarray) -> np.ndarray:
        """
        Description:
            Applies the image processing pipeline based on image type.

        Args:
            (1) image [np.ndarray]: Input image in uint8 format.

        Returns:
            (1) parameter [np.ndarray]: Processed image.
        """

        image_tmp = image.copy()

        if self.__image_type == 'synthetic':
            noisy_img = self.__Noise(image_tmp, std_dev=5.0)
            blurred_img = self.__Blur(noisy_img, kernel_size=(3, 3), sigma=0.5)
            styled_img = self.__Color_Style(blurred_img, alpha=0.95, beta=1)
            return self.__Blur(styled_img, kernel_size=(3, 3), sigma=1.0)
        elif self.__image_type == 'real':
            blurred_img = self.__Blur(image_tmp, kernel_size=(3, 3), sigma=0.5)
            return self.__Color_Style(blurred_img, alpha=0.95, beta=1)


    