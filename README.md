
# CLI Tools

This project contains a number of CLI tools written in Python for different personal purposes.




## Usage/Examples

### Deduplicate image files

This CLI moves identical image files. 

It doesn't require any dependencies, just python3.

```python
python file-tools/clean_identical_files.py --verbose --directory ~/images_not_sorted --target-directory /tmp/to-review --dry-run
```

  