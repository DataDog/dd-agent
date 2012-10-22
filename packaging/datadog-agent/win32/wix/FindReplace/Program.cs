using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.IO;

namespace FindReplace
{
    class Program
    {
        static void Main(string[] args)
        {            
            if (args.Length != 3)
            {
                Console.Write("Usage: FindReplace.exe path_to_file search_text replace_text\n");
                return;
            }         

            // Load in the arguments from the user
            String filePath = args[0];
            String searchText = args[1];
            String replaceText = args[2];

            // Don't overwrite the text with nothing
            if (replaceText.Trim() == "")
            {
                return;
            }

            // If we are given "key: val" but val doesn't exist, don't do the replacement
            String[] parts = replaceText.Split(new string[] {":"}, StringSplitOptions.None);
            if (parts.Length == 2 && parts[1].Trim() == "")
            {
                return;    
            }

            // Read the contents of the file
            String contents;

            try
            {
                contents = File.ReadAllText(filePath);
            }
            catch (Exception e)
            {
                Console.Write(String.Format("Unable to open file {0}, {1}", filePath, e));
                return;
            }

            // Replace all instances of the text in the file
            contents = contents.Replace(searchText, replaceText);

            // Write it back to the file
            try
            {
                File.WriteAllText(filePath, contents);
            }
            catch (Exception e)
            {
                Console.Write(String.Format("Unable to write contents to file {0}, {1}", filePath, e));
                return;
            }
        }
    }
}